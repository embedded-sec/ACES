//===- HexboxApplication.cpp - Example code from "Writing an LLVM Pass" ---------------===//
//
//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.
//
//===----------------------------------------------------------------------===//
//
// This file implements application of the HexBox policy
//
//===----------------------------------------------------------------------===//

#include "llvm/ADT/Statistic.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/CallSite.h"
#include "llvm/IR/Instructions.h"
#include "llvm/Pass.h"
#include "llvm/Support/raw_ostream.h"
#include <fstream>
#include <iostream>
#include "llvm/Support/Debug.h"
#include "llvm/Transforms/Instrumentation.h"
#include "llvm/ADT/SmallSet.h"
#include "llvm/ADT/DenseSet.h"
#include "llvm/Support/FileSystem.h"
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/InlineAsm.h"
#include "json/json.h" //From https://github.com/open-source-parsers/jsoncpp

using namespace llvm;

#define DEBUG_TYPE "hexbox"

//STATISTIC(Stat_NumFunctions, "Num Functions");

static cl::opt<std::string> HexboxPolicy("hexbox-policy",
                                  cl::desc("JSON Defining the policy"),
                                  cl::init("-"),cl::value_desc("filename"));
//#define NUM_MPU_REGIONS 8
#define ACCESS_ARRAY_SIZE 200

namespace {
  // Hello - The first implementation, without getAnalysisUsage.
  struct HexboxApplication : public ModulePass {
    static char ID; // Pass identification, replacement for typeid
    HexboxApplication () : ModulePass(ID) {}

    StringMap<GlobalVariable *> CompName2GVMap;
    DenseMap<Function *, Function *> Function2Wrapper;
    GlobalVariable * DefaultCompartment;

    bool doInitialization(Module &M) override{
        return true;
    }

  
    Constant * get_MPU_region_data(Module & M, StructType * RegionTy, unsigned int Addr, unsigned int Attr){
        SmallVector<Constant *,8> RegionsVec;
        APInt addr = APInt(32,Addr);
        APInt attr = APInt(32,Attr);
        RegionsVec.push_back(Constant::getIntegerValue(Type::getInt32Ty(M.getContext()), addr));
        RegionsVec.push_back(Constant::getIntegerValue(Type::getInt32Ty(M.getContext()), attr));
        Constant * Region = ConstantStruct::get(RegionTy,RegionsVec);
        return Region;
    }


    void buildGlobalVariablesForCompartments(Module &M, Json::Value & root){

        Json::Value comps =  root.get("MPU_CONFIG","");
        Json::Value num_mpu_regions =  root.get("NUM_MPU_REGIONS",8);
        unsigned comp_count =0;

        SmallVector<Type *,8> TypeVec;
        TypeVec.push_back(Type::getInt32Ty(M.getContext()));
        TypeVec.push_back(Type::getInt32Ty(M.getContext()));
        StructType * RegionTy = StructType::create(TypeVec,"__hexbox_md_regions");
        ArrayType * MPURegionTy = ArrayType::get(RegionTy,num_mpu_regions.asUInt());


        SmallVector<Type *,9> CompTyVec;

        CompTyVec.push_back(Type::getInt16Ty(M.getContext()));
        CompTyVec.push_back(Type::getInt8Ty(M.getContext()));
        CompTyVec.push_back(Type::getInt8Ty(M.getContext()));
        //CompTyVec.push_back(StatsArrayPtrTy);
        CompTyVec.push_back(MPURegionTy);
        StructType * CompTy = StructType::create(CompTyVec,"__hexbox_comparment");




        DEBUG(errs() << "Building Compartment Global Variables---------------------\n");


        for(auto CompName: comps.getMemberNames()){
            DEBUG(std::cout << "Compartment: "<< CompName);
            Json::Value Attrs = comps[CompName]["Attrs"];
            Json::Value Addrs = comps[CompName]["Addrs"];
            Json::Value Priv = root["Compartments"][CompName]["Priv"];
            DEBUG(std::cout << Attrs <<"\n");
            DEBUG(std::cout << Addrs <<"\n");

            /* Build MPU Regions */
            SmallVector<Constant *,16> MPURegionsVec;
            for(unsigned int i = 0; i<num_mpu_regions.asUInt();i++){
                Constant * Region;
                if (i < Attrs.size()){
                    Region = get_MPU_region_data(M, RegionTy, Addrs[i].asUInt(), Attrs[i].asUInt());
                }else{
                    Region = get_MPU_region_data(M, RegionTy, 0, 0);
                }
               MPURegionsVec.push_back(Region);
              }

            Constant * MPRegions = ConstantArray::get(MPURegionTy,MPURegionsVec);

            //Build Compartent
            SmallVector<Constant *,2> CompVec;
            APInt count = APInt(16,0);
            CompVec.push_back(Constant::getIntegerValue(Type::getInt16Ty(M.getContext()),count));

            APInt comp_id = APInt(8,comp_count);
            CompVec.push_back(Constant::getIntegerValue(Type::getInt8Ty(M.getContext()),comp_id));

            APInt priv = APInt(8,Priv.asInt());
            CompVec.push_back(Constant::getIntegerValue(Type::getInt8Ty(M.getContext()),priv));


            ++comp_count;
            CompVec.push_back(MPRegions);

            Constant * CompInit = ConstantStruct::get(CompTy,CompVec);
            GlobalVariable * Compartment = new GlobalVariable(M,CompTy,true, GlobalVariable::ExternalLinkage,CompInit,"_hexbox_comp_"+CompName);
            Compartment->setSection(".rodata");

            DEBUG(errs() << "Adding: "<<CompName<< "CompName: "<<Compartment->getName() << "\n");

            CompName2GVMap.insert(std::make_pair(CompName,Compartment));

        }

    }


    GlobalVariable * getCompartmentForFunction(Function *F){

        auto itr = CompName2GVMap.find(F->getSection());
        if (itr != CompName2GVMap.end()){
            return itr->second;
        }else{
            itr = CompName2GVMap.find("__hexbox_default");
            if (itr != CompName2GVMap.end()){
                DEBUG(errs() << "Looking up: "<< F->getName() << "\n");
                DEBUG(errs() << "Section: " <<F->getSection() << "\n");
                DEBUG(errs() << "Returning Default Comp\n");
                return itr->second;

            }else{
                assert(false && "No Default Hexbox Compartment found");
                return nullptr;
            }
        }

    }



    /*************************************************************************
    * interceptMain
    * This initializes hexbox.  It does it by renaming main to
    * __original_main and then creates a new main.  Taking the name main is
    * required because assembly is used to initialize the device and then calls
    * main. LLVM can analyze the assembly, so we hijack the symbol name.
    *
    * The main built initializes each compartment bss and data section, then
    *  
    */
    void interceptMain(Module & M,Json::Value PolicyRoot){

        Function * OrgMain = M.getFunction("main");
        Function * InitMain;
        IRBuilder<> *IRB;
        assert(OrgMain && "Main not found");
        OrgMain->setName("__original_main");
        DEBUG(OrgMain->getFunctionType()->dump());

        InitMain = Function::Create(OrgMain->getFunctionType(),OrgMain->getLinkage(),"main",&M);
        InitMain->addFnAttr(Attribute::NoUnwind);
        BasicBlock * BB = BasicBlock::Create(M.getContext(),"entry",InitMain);
        IRB = new IRBuilder<>(M.getContext());
        IRB->SetInsertPoint(BB);

        initBssAndDataSections(M,IRB,PolicyRoot);

        Function *HexboxStartFn = M.getFunction("__hexbox_start");

        assert(HexboxStartFn && "Function hexbox_start not found");
        SmallVector<Value *,1> Args;
        Constant * DefaultPolicy;
        DefaultPolicy = M.getGlobalVariable("_hexbox_comp___hexbox_default");

        assert(DefaultPolicy && "Default Compartment not found");

        DefaultPolicy = ConstantExpr::getInBoundsGetElementPtr(nullptr,DefaultPolicy,Constant::getNullValue(Type::getInt32Ty(M.getContext())));
        Value * V;

        V = IRB->CreateBitCast(DefaultPolicy,HexboxStartFn->getFunctionType()->getParamType(0));
        Args.push_back(V);

        IRB->CreateCall(HexboxStartFn,Args);

        Args.clear();
        for (auto & arg : InitMain->args()){
            Args.push_back(&arg);

        }

        V = IRB->CreateCall(OrgMain,Args);
        SmallVector<Function *,12> Callees;
        Callees.push_back(OrgMain);
        CallSite cs = CallSite(V);
        addTransition(M,cs,Callees);
        IRB->CreateUnreachable();

        delete IRB;

    }


    void insertHexboxInit(Module & M, Json::Value PolicyRoot){
        interceptMain(M,PolicyRoot);
    }


    /**************************************************************************
     * addDataInitToMain
     * adds initialization of a Hexbox Data section to start of main
     *
     *************************************************************************/
    void addDataInit(Module & M, IRBuilder<> *IRB, StringRef &startName, \
                           StringRef &stopName, StringRef &vmaName){
        Function * SectionInit;
        SectionInit=M.getFunction("__hexbox_init_data_section");
        assert(SectionInit && "Can't find initialization routine check RT Lib");
        Type * arg0Type = Type::getInt32Ty(M.getContext());;
        Type * arg1Type = Type::getInt32Ty(M.getContext());;
        Type * arg2Type = Type::getInt32Ty(M.getContext());;

        Value *StartAddr =M.getOrInsertGlobal(startName,arg1Type);
        Value *StopAddr = M.getOrInsertGlobal(stopName,arg2Type);
        Value *VMAAddr = M.getOrInsertGlobal(vmaName,arg0Type);
        assert(StartAddr && StopAddr && VMAAddr && \
               "Data Section Addresses Need but not found");
        std::vector<Value *> CallParams;

        StartAddr = IRB->CreateIntToPtr(StartAddr,\
                                        Type::getInt32PtrTy(M.getContext()));
        StopAddr = IRB->CreateIntToPtr(StopAddr,\
                                       Type::getInt32PtrTy(M.getContext()));
        VMAAddr = IRB->CreateIntToPtr(VMAAddr,\
                                      Type::getInt32PtrTy(M.getContext()));

        CallParams.push_back(VMAAddr);
        CallParams.push_back(StartAddr);
        CallParams.push_back(StopAddr);
        IRB->CreateCall(SectionInit,CallParams);
    }


    /**************************************************************************
     * addBssInit
     * adds initialization of a Hexbox bss section to start of main
     *
     *************************************************************************/
    void addBssInit(Module & M, IRBuilder<> * IRB,StringRef & startName, \
                          StringRef & stopName){
        Function * SectionInit;

        SectionInit=M.getFunction("__hexbox_init_bss_section");
        assert(SectionInit && "Can't find initialization routine check RT Lib");


        Type * arg0Type = Type::getInt32Ty(M.getContext());
        Type * arg1Type = Type::getInt32Ty(M.getContext());

        Value *StartAddr = M.getOrInsertGlobal(startName,arg0Type);
        Value *StopAddr = M.getOrInsertGlobal(stopName,arg1Type);

        assert(StartAddr && StopAddr && \
               "BSS Section Addresses Need but not found");
        std::vector<Value *> CallParams;

        StartAddr = IRB->CreateIntToPtr(StartAddr,\
                                        Type::getInt32PtrTy(M.getContext()));
        StopAddr = IRB->CreateIntToPtr(StopAddr,\
                                       Type::getInt32PtrTy(M.getContext()));
        CallParams.push_back(StartAddr);
        CallParams.push_back(StopAddr);
        IRB->CreateCall(SectionInit,CallParams);
    }

     void initBssAndDataSections(Module &M, IRBuilder<> * IRB, Json::Value &Root){
        Json::Value PolicyRegions=Root.get("Regions","");
        for(auto RegionName: PolicyRegions.getMemberNames()){
            Json::Value Region = PolicyRegions[RegionName];
            Json::Value region_type = Region["Type"];
            if ( region_type.compare("Data") == 0 ){
                DEBUG(std::cout << "Initializing Data Region\n");
                //std::string DataSection(RegionName+"_data");
                //std::string BSSSection(RegionName+"_bss");
                bool DataUsed = false;
                bool BSSUsed = false;

                for (auto gvName : Region.get("Objects","")){
                     DEBUG(std::cout << gvName.asString() <<"\n");
                     GlobalVariable *GV;
                     GV = M.getGlobalVariable(StringRef(gvName.asString()),true);
                     if (GV){
                         DEBUG(errs() << "Adding "<<GV->getName() << " to ");
                         if ( GV->hasInitializer() ){
                             if (GV->getInitializer()->isZeroValue()){
                                BSSUsed=true;
                             }else{
                                DataUsed=true;
                             }
                         }else{
                             assert(false &&"GV Has no initializer");
                         }
                     }
                     else{
                         DEBUG(std::cout << "No Name GV for: "<< gvName <<"\n");
                     }
                 }//for
                if(BSSUsed){
                    std::string startVar = RegionName + "_bss_start";
                    std::string stopVar = RegionName + "_bss_end";
                    StringRef BSSStartVar = StringRef(startVar);
                    StringRef BSSEndVar = StringRef(stopVar);
                    addBssInit(M,IRB,BSSStartVar,BSSEndVar);
                }
                if(DataUsed){
                    std::string startVar = RegionName + "_data_start";
                    std::string stopVar =  RegionName + "_data_end";
                    std::string vmaStart = RegionName+"_vma_start";
                    StringRef LMAVar = StringRef(vmaStart);
                    StringRef DataStartVar = StringRef(startVar);
                    StringRef DataEndVar = StringRef(stopVar);
                    addDataInit(M,IRB, DataStartVar, DataEndVar, LMAVar);
                }
            }
        }
    }

    /**
     assignLinkerSections
     Reads the sections from the policy file and assigns functions and globals
     to specific sections.  These sections define tell the linker where to place
     the functions and globals. They compose regions of a compartment

    */
    void assignLinkerSections(Module &M, Json::Value &Root){
        Json::Value PolicyRegions=Root.get("Regions","");
        for(auto RegionName: PolicyRegions.getMemberNames()){
            Json::Value Region = PolicyRegions[RegionName];
            Json::Value region_type = Region["Type"];
            if ( region_type.compare("Code") == 0 ){
                for (auto funct : Region.get("Objects","")){
                    Function * F = M.getFunction(StringRef(funct.asString()));
                    if (F){
                        F->setSection(StringRef(RegionName));
                    }else{
                        std::cout << "No Name Function for: "<< funct <<"\n";
                    }
                }
            }else{
                std::string DataSection(RegionName+"_data");
                std::string BSSSection(RegionName+"_bss");
                for (auto gvName : Region.get("Objects","")){
                    GlobalVariable *GV;
                    GV = M.getGlobalVariable(StringRef(gvName.asString()),true);
                    if (GV){
                        if ( GV->hasInitializer() ){
                            if (GV->getInitializer()->isZeroValue()){
                                GV->setSection(StringRef(BSSSection));
                             }else{
                                GV->setSection(StringRef(DataSection));
                             }
                         }else{
                             assert(false &&"GV Has no initializer");
                         }
                     }
                     else{
                         std::cout << "No Name GV for: "<< gvName <<"\n";
                     }
                 }//for
            }
        }
    }

    /**
     * @brief buildCompartments
     * @param M : The Module
     * @param policy : The policy
     *
     * Reads the Compartment info from the policy file.  This defines what
     * section should be put together to form a compartment. It builds the
     * global data for each compartment, and the identifies and instruments
     * compartment entries and exits
     */
    void buildCompartments(Module & M, Json::Value & policy){

        buildGlobalVariablesForCompartments(M,policy);
        identifyTransitions(M,policy);

    }


    GlobalVariable * getMetadata(Module &M,SmallVector<Function *,12> &callees, Instruction * callInst){
        // Builds the metadata {return_policy, dest_count, [{dest_ptr,compartment},...]
        SmallVector<Type *,4> MDTypeVec;
        SmallVector<Constant *,6> MDValues;
        GlobalVariable * CompartmentGV = getCompartmentForFunction(callInst->getFunction());
        Constant * C;

        C = ConstantExpr::getInBoundsGetElementPtr(nullptr,CompartmentGV,Constant::getNullValue(Type::getInt32Ty(M.getContext())));
        MDValues.push_back(C);
        MDTypeVec.push_back(C->getType()); //return compartment

        C = Constant::getIntegerValue(Type::getInt32Ty(M.getContext()),APInt(32,callees.size()));
        MDValues.push_back(C);
        MDTypeVec.push_back(C->getType());

        errs() << "----------- Building Meta Data --------------------\n";
        errs() << "Function: " <<callInst->getFunction()->getName()<<"\n";
        for (Function * callee: callees){
            errs() << "Callee: " <<callee->getName() <<"\n";
            MDValues.push_back(callee);
            MDTypeVec.push_back(callee->getType());  //destinations

            CompartmentGV = getCompartmentForFunction(callee);
            C = ConstantExpr::getInBoundsGetElementPtr(nullptr,CompartmentGV,Constant::getNullValue(Type::getInt32Ty(M.getContext())));
            MDTypeVec.push_back(C->getType());
            MDValues.push_back(C);

        }
        errs() << "----------- End metadata --------------------\n";

        StructType * MDTy = StructType::create(MDTypeVec);
        Constant * MDInit = ConstantStruct::get(MDTy,MDValues);
        GlobalVariable * GV_MD = new GlobalVariable(M,MDInit->getType(),true,
                                                 GlobalVariable::ExternalLinkage,MDInit,"__hexbox_md");
        GV_MD->setSection(".rodata");


        return GV_MD;
    }


    void addTransition(Module & M, CallSite & cs,SmallVector<Function *,12> &callees){
        GlobalVariable * md;

        if (CallInst * ci = dyn_cast<CallInst>(cs.getInstruction())){ 
            md = getMetadata(M,callees,ci);
            ci->setHexboxMetadata(md);
            for (Function * callee : callees){
                //callee->setIsHexboxEntry(true);
                DEBUG(errs() << "\t" <<callee->getName() << ";");
                callee->addFnAttr("HexboxEntry","true");

            }

        }else{
            assert(true && "HexBoxApplication:CallSite not a CallInst");
        }
    }


    bool isTransition(Module &M, Function *CurFunct, CallSite &cs){
        SmallVector<Function *,12> callees;
        Function * callee = cs.getCalledFunction();
        if ( callee ){
            callees.push_back(callee);
        }else if (ConstantExpr * ConstEx = dyn_cast_or_null<ConstantExpr>(cs.getCalledValue())){
            Instruction * Inst = ConstEx->getAsInstruction();
            if( CastInst * CI = dyn_cast_or_null<CastInst>(Inst) ){
                if ( Function * c = dyn_cast<Function>(Inst->getOperand(0)) ){ 
                        callees.push_back(c);


                }else{
                    assert(false && "Unhandled Cast");
                }
            }else{
                assert(false && "Unhandled Constant");
            }
            delete Inst;
        }else{

            getIndirectTargets(M, cs, callees);
        }

        SmallVector<Function *,12>InstrumentCallees;
         for (Function * F :callees){
             if (F->getSection() == CurFunct->getSection()){
                F->addFnAttr("HexboxInternalCall");
             }
             if (F->getName().startswith("__hexbox")){
                 ;
             }
             else if (F->getName().startswith("llvm.")){
                 ;
             }
             else if (F->isIntrinsic() || F->isDeclaration()){
                 errs() << "Found Declaration in call: "<<F->getName() <<"\n";
                 errs() << "Function: " << cs->getFunction()->getName() << "\n";
                 cs->dump();

             }
             else{
                 InstrumentCallees.push_back(F);
             }

         }

        for (Function * F :InstrumentCallees){
            DEBUG(errs() << "sections: " << CurFunct->getSection() << " ; " );
            DEBUG(errs() << F->getName() << ":" << F->getSection() << "\n");
            if (F->getSection() != CurFunct->getSection()){
                addTransition(M,cs, callees);
                DEBUG(errs() << "Adding Transition\n");
                return true;
            }
        }
        return false;
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

 
    void getIndirectTargets(Module & M, CallSite & cs,
                            SmallVector<Function *,12> &callees ){
        std::string str;
        raw_string_ostream callee_name(str);
        FunctionType * IndirectType;

        IndirectType = cs.getFunctionType();
        for (Function & F : M.getFunctionList()){
            if (F.getName().startswith("__hexbox") || F.isIntrinsic()|| \
                    F.hasFnAttribute("HexboxWrapper")){
                continue;
            }
            if ( TypesEqual(IndirectType,F.getFunctionType()) && F.hasAddressTaken() ){
                callees.push_back(&F);
            }
        }
    }


    /**
     * @brief identifyTransitions
     * @param policyFile
     * @param M
     *
     * For each function identify all call sites and their possible destinations.
     *
     */
    //USED
    void identifyTransitions(Module &M, Json::Value & policyFile){
        SmallSet<Function*,10> ISRs;
        for (Function & F : M.getFunctionList()){
            if (F.isIntrinsic() || F.isDeclaration()||F.getName().startswith("__hexbox")){
                continue;
            }
            DEBUG(errs() << "___________________________________________\n");
            DEBUG(errs().write_escaped(F.getName())<<"\n");
            for ( BasicBlock &BB : F ){
                for ( Instruction & I : BB ){
                    if ( CallSite cs = CallSite(&I) ){
                        if (!isa<InlineAsm>(cs.getCalledValue())){
                            DEBUG(errs() << "Checking Callsite: ");
                            DEBUG(cs->dump());
                            isTransition(M,&F,cs);
                            if(F.getSection().equals(StringRef(".IRQ_CODE_REGION"))&& \
                                    (! F.getName().equals("SVC_Handler"))){
                                ISRs.insert(&F);
                            }
                        }
                    }
                }
            }

            DEBUG(errs() << "-------------------------------------------\n");
        }

    }


    /**************************************************************************
     * runOnModule
     * Reads in a policy JSON file and moves functions and data to the
     * designated regions
     *
     *************************************************************************/
    bool runOnModule(Module &M) override {

        if ( HexboxPolicy.compare("-") == 0 )
            return false;

        //Read in Policy File
        Json::Value PolicyRoot;
        std::ifstream policyFile;
        policyFile.open(HexboxPolicy);
        policyFile >> PolicyRoot;

        assignLinkerSections(M,PolicyRoot);
        buildCompartments(M,PolicyRoot);
        insertHexboxInit(M,PolicyRoot);

      return true;
    }



    bool doFinalization(Module &M) override{

        if ( HexboxPolicy.compare("-") == 0 )
            return false;

        return false;
    }


    void getAnalysisUsage(AnalysisUsage &AU) const override {
      //AU.setPreservesAll();
    }
  };

}
char HexboxApplication::ID = 0;
INITIALIZE_PASS(HexboxApplication, "HexboxApplication", "Applies specified hexbox policy", false, false)



ModulePass *llvm::createHexboxApplicationPass(){
  DEBUG(errs() << "Hexbox Application Pass" <<"\n");
  return new HexboxApplication();
}


