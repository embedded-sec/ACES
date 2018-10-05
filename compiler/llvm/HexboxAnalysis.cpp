//===- HexboxAnalysis.cpp -------------------------------------------------===//
//
//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.
//
//===----------------------------------------------------------------------===//
//
// This file performs analysis of the application to generate data that can
// be used to create a HexBox policy
//
//===----------------------------------------------------------------------===//

#include "llvm/ADT/Statistic.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/CallSite.h"
#include "llvm/IR/Instructions.h"
#include "llvm/Pass.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/Support/Debug.h"
#include "llvm/Transforms/Instrumentation.h"
#include "llvm/ADT/SmallSet.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/DebugInfoMetadata.h"
#include "json/json.h"  //From https://github.com/open-source-parsers/jsoncpp
#include <fstream>


#include "llvm/IR/InstIterator.h"


using namespace llvm;

#define DEBUG_TYPE "hexbox"

STATISTIC(NumFunctions, "Num Functions");

static cl::opt<std::string> HexboxAnalysisResults("hexbox-analysis-results",
                                  cl::desc("JSON File to write analysis results to"),
                                  cl::init("-"),cl::value_desc("filename"));

namespace {

  struct HexboxAnalysis : public FunctionPass {
    static char ID;
    HexboxAnalysis() : FunctionPass(ID) {
        initializeHexboxAnalysisPass(*PassRegistry::getPassRegistry());
    }

    Json::Value OutputJsonRoot;

    /******************************AddFunctionToJSON**************************
    * Adds the function to the Root Json value, along with all callers and
    * callees.  Also initializes the Globals object under the function
    *
    *************************************************************************/
    Json::Value & AddFunctionToJSON(Function & F){
        std::string name = F.getName().str();
        Json::Value *Fnode;
        Json::Value *Attr;
        std::string str;
        raw_string_ostream type_name_stream(str);
        F.getType()->print(type_name_stream);


        Fnode = &OutputJsonRoot[name];
        Attr = &(*Fnode)["Attr"];


        (*Attr)["Type"]="Function";
        (*Attr)["Address Taken"]= F.hasAddressTaken();
        (*Attr)["LLVM_Type"] = type_name_stream.str();
        DISubprogram * SP = F.getSubprogram();
        if ( SP ){
            std::string filename = SP->getFile()->getFilename().str();

            (*Attr)["Filename"] = filename;
        }

        //Adds Callers
        std::vector<Json::Value> Cons;
        for (User * U: F.users()){
            if (Instruction * Inst = dyn_cast<Instruction>(U)){
                if (auto cs = CallSite(Inst)){
                    Function * caller = cs.getCaller();
                    add_connection(*Fnode,caller->getName().str(),"Caller");
                }
            }
        }

        //Adds Callees
        for ( BasicBlock &BB : F ){
            for ( Instruction & I : BB ){
                if ( CallSite cs = CallSite(&I) ){
                    if (cs){
                        Function * callee = cs.getCalledFunction();
                        if ( callee ){
                            add_connection(*Fnode,callee->getName().str(),"Callee");

                        }else if ( InlineAsm * IA = dyn_cast_or_null<InlineAsm>(cs.getCalledValue()) ){
                            std::string str;
                            raw_string_ostream callee_name(str);
                            cs->print(callee_name);
                            add_connection(*Fnode,callee_name.str(),"Asm Callee");

                        }else if (ConstantExpr * ConstEx = dyn_cast_or_null<ConstantExpr>(cs.getCalledValue())){
                            Instruction * Inst = ConstEx->getAsInstruction();
                            if( CastInst * CI = dyn_cast_or_null<CastInst>(Inst) ){
                                if ( Function * c = dyn_cast<Function>(Inst->getOperand(0)) ){
                                    add_connection(*Fnode,c->getName().str(),"Callee");

                                }else{
                                    assert(false && "Unhandled Cast");
                                }
                            }else{
                                assert(false && "Unhandled Constant");
                            }
                            delete Inst;
                        }else{
                            add_indirect_calls(*Fnode, F, I, cs);
                        }
                    }
                }
            }
        }
        return (*Fnode);
    }


    void add_connection(Json::Value & Fnode, std::string name ,std::string type){
        Json::Value *Connections;
        Connections = &Fnode["Connections"][name];
        (*Connections)["Type"] = type;
        (*Connections)["Count"] = (*Connections)["Count"].asUInt64() + 1;
    }


    bool TypesEqual(Type *T1,Type *T2,unsigned depth = 0){

        if ( T1 == T2 ){
            return true;
        }
        if (depth > 10){
            // If we haven't found  a difference this deep just assume they are
            // the same type. We need to overapproximate (i.e. say more things
            // are equal than really are) so return true
            return true;
        }
        if (PointerType *Pty1 = dyn_cast<PointerType>(T1) ){
            if (PointerType *Pty2 = dyn_cast<PointerType>(T2)){
            return TypesEqual(Pty1->getPointerElementType(),
                              Pty2->getPointerElementType(),depth+1);
            }else{
                return false;
            }
        }
        if (FunctionType * FTy1 = dyn_cast<FunctionType>(T1)){
            if (FunctionType * FTy2 = dyn_cast<FunctionType>(T2)){

                if (FTy1->getNumParams() != FTy2->getNumParams()){
                    return false;
                }
                if (! TypesEqual(FTy1->getReturnType(),
                                 FTy2->getReturnType(), depth+1)){
                    return false;
                }
                for (unsigned i=0; i<FTy1->getNumParams(); i++){
                    if (FTy1->getParamType(i) == FTy1 &&
                          FTy2->getParamType(i) == FTy2  ){
                        continue;
                    }else if (FTy1->getParamType(i) != FTy1 &&
                              FTy2->getParamType(i) != FTy2  ){
                        FTy1->getParamType(i)->dump();
                        FTy2->getParamType(i)->dump();
                        if( !TypesEqual(FTy1->getParamType(i),
                                        FTy2->getParamType(i), depth+1)){
                         return false;
                        }
                    }else{
                        return false;
                    }
                }
                return true;

            }else{
                return false;
            }
        }
        if (StructType *STy1 = dyn_cast<StructType>(T1)){
            if (StructType *STy2 = dyn_cast<StructType>(T2)){
                if(STy2->getNumElements() != STy1->getNumElements()){
                    return false;
                }
                if(STy1->hasName() && STy2->hasName()){
                    if(STy1->getName().startswith(STy2->getName()) ||
                        STy2->getName().startswith(STy1->getName())){
                        return true;
                    }
                }
                return false;

            }else{
                return false;
            }
        }
        return false;
    }


    void add_indirect_calls(Json::Value & Fnode, Function & F, Instruction & I, CallSite & cs ){
        std::string str;
        raw_string_ostream callee_name(str);
        std::string str2;
        raw_string_ostream callee_type_str(str2);
        FunctionType * IndirectType;
        Json::Value *Indirect;
        I.print(callee_name);
        Indirect = &OutputJsonRoot[callee_name.str()];
        (*Indirect)["Attr"]["Type"] = "Indirect";


        (*Indirect)["Attr"]["Function"] = I.getFunction()->getName().str();

        add_connection(Fnode,callee_name.str(),"Indirect Call Type");
        IndirectType = cs.getFunctionType();
        IndirectType->print(callee_type_str);
        (*Indirect)["Attr"]["LLVMType"] = callee_type_str.str();
        for (Function & Funct : F.getParent()->getFunctionList()){
            //if ( IndirectType == Funct.getFunctionType() &&
            if ( TypesEqual(IndirectType,Funct.getFunctionType()) &&
                 Funct.hasAddressTaken() ){
                add_connection(Fnode,Funct.getName().str(),"Indirect Call");
                add_connection(*Indirect,Funct.getName().str(),"Indirect Call");
            }
        }
    }

    class DataDependancy{

    public:
        SmallSet<Function *,32> functions;

        DataDependancy(Value * v,Type * t,const DataLayout & DL,unsigned ad=0){
            V = v;
            read = false;
            write = false;
            isArg = false;
            isParam = false;
            argNum = 0;
            ty = t;
            addr = ad;
            determineSize(DL);
            id = dd_class_id;
            dd_class_id++;

        }

        bool getRead(){
            return read;
        }
        bool getWrite(){
            return write;
        }

        void setIsArg(unsigned n){
            isArg =true;
            argNum = n;
        }

        void setIsParam(unsigned n){
            isParam =true;
            argNum = n;
        }
        void add_function(Function *F){
            functions.insert(F);
        }

        unsigned getAddr(){
            return addr;
        }

        unsigned getSize(){
            return size;
        }

        void WriteNode(Json::Value &JsonNode){
            std::stringstream ss;
            ss << ".Peripheral_"<<id;
            Json::Value & ThisNode = JsonNode[ss.str()];
            errs()<< "Writing Json Node: " << ss.str() <<"\n";
            writeJsonAttributes(ThisNode["Attr"]);
            for (Function * F : functions){
                ThisNode["Connections"][F->getName()]["Type"]="Peripheral";
            }

        }

        bool inside(unsigned value){

            if (this->addr <= value && value < this->addr+this->size){
                return true;
            }
            return false;
        }


        bool overlap(DataDependancy *DD){
            if (inside(DD->getAddr()) || DD->inside(this->addr)){
                 return true;
            }
            return false;
        }

        void determineSize(const DataLayout & DL){
            size = 0;
            if(ty){
                if(PointerType * PT = dyn_cast<PointerType>(ty)){
                    size = DL.getTypeAllocSize(PT->getElementType());
                }
                else{
                   size = DL.getTypeAllocSize(ty);
                }

            }
        }

        void writeJsonAttributes(Json::Value & Rnode){
            std::string s;
            raw_string_ostream  stream(s);

            if (addr){
                Rnode["Type"] = "Peripheral";
                Rnode["Addr"] = addr;

            }
            if (V->hasName()){
                Rnode["Name"] = V->getName().str();
            }
            if(ty){
                ty->print(stream);
                Rnode["DataType"] =stream.str();
                Rnode["DataSize"] = size;
            }
            Rnode["Read"] = read;
            Rnode["Write"] = write;
            std::string st;
            raw_string_ostream ss(st);
            V->print(ss);
            Rnode["LLVM::Value"] =ss.str();
            Rnode["IsArg"] = isArg;
            Rnode["IsParam"] = isParam;
            Rnode["ArgNum"] = argNum;

        }
        void updateProperties(Value *v){
            if(isa<LoadInst>(v)){
                read = true;
            }else if (isa<StoreInst>(v)){
                write = true;
            }
        }

        void determineAttributes(Value * v){
            errs() << "Determining Attributes\n";
            v->dump();
            if(Instruction * I =dyn_cast<Instruction>(v)){
                errs() << "Adding Function ";
                errs().write_escaped(I->getFunction()->getName());
                errs()<< "\n";
                functions.insert(I->getFunction());
                if(CallInst * CI = dyn_cast<CallInst>(v)){
                    SmallSet<Function *,32> Callees;
                    getPotentialCallees(CI,Callees);
                    for(Function * Callee : Callees){
                        functions.insert(Callee);
                    }
                }else if(isa<LoadInst>(v)){
                    read = true;
                }else if (isa<StoreInst>(v)){
                    write = true;
                }
            }else{
                for(User * U: v->users()){
                    determineAttributes(U);
                }
            }
        }

    private:

        unsigned id;
        Value * V;
        bool read;
        bool write;
        bool isArg;
        bool isParam;
        unsigned argNum;
        unsigned addr;
        unsigned size;
        Type * ty;
    };

    static unsigned dd_class_id;


    static void getPotentialCallees(CallInst * CI,SmallSet<Function *,32> &Callees){
        Function *Callee = CI->getCalledFunction();

        if (Callee){
            Callees.insert(Callee);
        }else{
            for(auto & Fun : CI->getFunction()->getParent()->functions()){
                 if (Fun.getFunctionType() == CI->getFunctionType()){
                     Callees.insert(&Fun);
                 }
            }
        }
    }


    void getFunctionResources(Module * M){
        DenseMap<Function *,DenseMap<Value *,DataDependancy*>> DependanceMap;

        SmallSet<Constant *,32> PeripheralWorklist;
        SmallSet<Value *,32>LocalWorklist;
        SmallSet<GlobalVariable *,32> GlobalWorklist;

        for (Function & F :M->functions()){
            if(F.getName().startswith("llvm.dbg.")){
                continue;
            }
            for (inst_iterator itr=inst_begin(F); itr!=inst_end(F);++itr){
                Instruction *I = &*itr;
                for (unsigned i=0;i<I->getNumOperands();i++){
                    Value *V = I->getOperand(i);
                    if(ConstantExpr *C = dyn_cast<ConstantExpr>(V)){
                        PeripheralWorklist.insert(C);
                    }else if (AllocaInst *AI = dyn_cast<AllocaInst>(V)){
                        LocalWorklist.insert(AI);
                    }else if (GlobalVariable *GV = dyn_cast<GlobalVariable>(V)){
                        GlobalWorklist.insert(GV);
                    }
                }
            }
            AddFunctionToJSON(F);
        }

        getPeripheralDependancies(PeripheralWorklist,M->getDataLayout());

    }


    void getPeripheralDependancies(SmallSet<Constant *,32> &Worklist, const DataLayout & DL){

        DataDependancy * DD;

        for (auto * C : Worklist){
            unsigned addr;
            Type * ty=nullptr;
            errs() << "Checking Constant: ";
            C->dump();
            addr = getConstIntToPtr(C,ty);
            if (addr != 0){
                DD = new DataDependancy(C,ty,DL,addr);
                errs() << "Creating DD: ";
                C->dump();
                for (User * U : C->users()){
                    DD->determineAttributes(U);

                }
                DD->WriteNode(OutputJsonRoot);
                delete DD;
            }
        }

    }


    unsigned getConstIntToPtr(Value * V,Type * &ty){
        unsigned addr = 0;
        if (IntToPtrInst * I2P = dyn_cast<IntToPtrInst>(V)){
            Value *Val = I2P->getOperand(0);
            if (ConstantInt * CInt = dyn_cast<ConstantInt>(Val)){
                addr = CInt->getValue().getLimitedValue(0xFFFFFFFF);
                ty = I2P->getType();

                errs() << "Int: " << addr << "\n";
                errs()<<"Type: "; ty->dump();
                return addr;
            }else{
                return 0;
            }
        }else if (Instruction * I = dyn_cast<Instruction>(V)){
            for (unsigned i=0;i<I->getNumOperands();i++){
                addr = getConstIntToPtr(I->getOperand(i),ty);
                if (addr){
                    return addr;
                }
            }
        }else if (ConstantExpr * C = dyn_cast<ConstantExpr>(V)){
            Instruction *Instr = C->getAsInstruction();
            addr = getConstIntToPtr(Instr,ty);
            delete(Instr);
        }else{
            return 0;
        }
        return addr;
    }


    /**
     * @brief doInitialization
     * @param M
     * @return
     */
    bool doInitialization(Module &M) override{
        if ( HexboxAnalysisResults.compare("-") == 0 ){
            return false;
        }

        for (GlobalVariable &GV : M.globals()){
            if( GV.hasInitializer() && !GV.getName().startswith(".") ){
                addFunctionUses(GV,&GV,M);
             }else{
                errs() << "GV Has no Initializer:";
                GV.dump();
            }

        }

        getFunctionResources(&M);

        return false;
    }


    StringRef getPassName() const override {
        return StringRef("HexboxAnalysis");
    }


    bool runOnFunction(Function & F) override {



        if ( HexboxAnalysisResults.compare("-") == 0 ){
            return false;
        }


        NumFunctions++;



        return false;
    }


    void addFunctionUses(GlobalVariable & GV, Value * V, Module & M){
         for (User * U : V->users()){
             Json::Value * Global;
             Function * F = nullptr;


             if ( Instruction * I = dyn_cast<Instruction>(U) ) {
                 F = I->getFunction();
                 Global = &OutputJsonRoot[GV.getName().str()];
                 add_connection(*Global,F->getName().str(),"Data");
                 (*Global)["Attr"]["Type"]="Global";
                 (*Global)["Attr"]["Size"] = M.getDataLayout().getTypeAllocSize(GV.getType());
                 // Don't know why you use 0 in the getMetadata() below but I've tried a bunch of other options
                 // like Metadata::DIGlobalVariableExpressionKind etc and always get null
                 if ( DIGlobalVariableExpression * DI_GVE = dyn_cast_or_null<DIGlobalVariableExpression>(GV.getMetadata(0)) ){
                        (*Global)["Attr"]["Filename"] = DI_GVE->getVariable()->getFilename().str();
                 }
             }else if ( Constant * C = dyn_cast<Constant>(U) ){
                 addFunctionUses(GV,C,M);
             }else{
                 errs() << "Unknown Use";
                 U->dump();
             }
         }

    }


    bool doFinalization(Module &M) override{

        if ( HexboxAnalysisResults.compare("-") == 0 ){
            return false;
        }

        std::ofstream jsonFile;
        jsonFile.open(HexboxAnalysisResults);
        jsonFile <<OutputJsonRoot;
        jsonFile.close();

        return false;
    }


    // We don't modify the program, so we preserve all analyses.
    void getAnalysisUsage(AnalysisUsage &AU) const override {

        AU.setPreservesAll();

    }
  };

}


unsigned HexboxAnalysis::dd_class_id =0;
char HexboxAnalysis::ID = 0;
INITIALIZE_PASS_BEGIN(HexboxAnalysis, "HexboxAnaysis", "Performs HexBox LLVM Analysis",false, false)
INITIALIZE_PASS_END(HexboxAnalysis, "HexboxAnaysis", "Performs HexBox LLVM Analysis",false, false)


FunctionPass *llvm::createHexboxAnalysisPass(){
  return new HexboxAnalysis();
}
