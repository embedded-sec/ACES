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
#include "llvm/ADT/ilist.h"
#include "llvm/Pass.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/Support/Debug.h"
#include "llvm/Transforms/Instrumentation.h"
#include "llvm/ADT/SmallSet.h"
#include "llvm/ADT/DenseSet.h"
#include "llvm/Support/FileSystem.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/Metadata.h"
#include "llvm/IR/DebugInfoMetadata.h"
#include "json/json.h"  //From https://github.com/open-source-parsers/jsoncpp
#include <fstream>
#include <iostream>
#include "llvm/Analysis/CFLAndersAliasAnalysis.h"
#include "llvm/Analysis/TypeBasedAliasAnalysis.h"

#include "llvm/IR/InstIterator.h"
#include "llvm/Analysis/AliasAnalysis.h"
#include "llvm/Analysis/BasicAliasAnalysis.h"
#include "llvm/Analysis/GlobalsModRef.h"
#include "llvm/Analysis/ScalarEvolutionAliasAnalysis.h"

using namespace llvm;

#define DEBUG_TYPE "hexbox"

STATISTIC(NumAliases, "Num Aliases");
STATISTIC(NumArgs, "Num Args");

static cl::opt<std::string> ExperiementAnalysisResults("experiment-analysis-results",
                                  cl::desc("JSON File to write analysis results to"),
                                  cl::init("-"),cl::value_desc("filename"));

namespace {
  // Hello - The first implementation, without getAnalysisUsage.
  struct ExperimentAnalysis : public FunctionPass {
    static char ID; // Pass identification, replacement for typeid
    ExperimentAnalysis() : FunctionPass(ID) {
        initializeExperimentAnalysisPass(*PassRegistry::getPassRegistry());
    }


    /**
     * @brief doInitialization
     * @param M
     * @return
     */
    bool doInitialization(Module &M) override{
        NumAliases = 0;
        NumArgs = 0;
        return false;
    }


    StringRef getPassName() const override {
        return StringRef("ExperimentAnalysis");
    }


    bool runOnFunction(Function & F) override {
        /*
          SmallSet<GlobalVariable*,8> AccessedGV;
          SmallSet<GlobalVariable*,8> GVsToCheck;

          SmallSet<Value *,8>AccessedArgs;
          SmallSet<Value *,8> ArgsToCheck;


          errs() << "-------------------------------------------------------\n";
          errs() << "Checking: " << F.getName() << "\n";
          errs() << "-------------------------------------------------------\n";
          AAResults * AA = &getAnalysis<AAResultsWrapperPass>().getAAResults();
*/
          /*
          if (auto *WrapperPass = getAnalysisIfAvailable<CFLAndersAAWrapperPass>()){
              errs() << "Adding AndersAA\n";
              AA->addAAResult(WrapperPass->getResult());
          }*/


          /*if (auto *WrapperPass = getAnalysisIfAvailable<GlobalsAAWrapperPass>()){
              errs() << "Adding GlobalsAA\n";
              AA->addAAResult(WrapperPass->getResult());
          }*/

          /*if (auto *WrapperPass = getAnalysisIfAvailable<TypeBasedAAWrapperPass>()){
              errs() << "Adding TBAA\n";
              AA->addAAResult(WrapperPass->getResult());
          }*/


        /*
          for (GlobalVariable &GV: F.getParent()->globals()){
              //errs() << "Adding Global: " << GV.getName() << "\n";
              GVsToCheck.insert(&GV);

          }

          for (Argument &A :F.getArgumentList()){
              if (A.getType()->isPointerTy()){
                  //errs() << "Adding Arg:";
                  A.dump();
                  ArgsToCheck.insert(&A);

              }
          }



          for (inst_iterator itr=inst_begin(F); itr!=inst_end(F);++itr){
              Instruction *I = &*itr;
              if (I->mayReadOrWriteMemory()){
                  for (auto U_itr = I->op_begin() ; U_itr != I->op_end() ; ++U_itr){
                      Use * U = &*U_itr;
                      if(U->get()->getType()->isPointerTy()){
                          for (auto GV_itr=GVsToCheck.begin(); GV_itr!=GVsToCheck.end(); ++GV_itr){
                              GlobalVariable * GV = *GV_itr;
                              if (! AA->isNoAlias(GV,U->get())){
                                  AccessedGV.insert(GV);
                                  //errs() << "May Access: " <<GV->getName() << "\n";
                                  GVsToCheck.erase(GV);
                                  NumAliases++;
                              }

                          }
                      }
                      for (auto argItr =ArgsToCheck.begin(); argItr!=ArgsToCheck.end();++argItr){
                          Value *A = *argItr;
                          if (! AA->isNoAlias(A,U->get())){
                              AccessedArgs.insert(A);
                              //errs() << "Arg Accessed: ";
                              A->dump();
                              NumArgs++;
                              ArgsToCheck.erase(A);
                          }
                      }
                  }
              }

          }
          errs() << "May Alias Size: " << AccessedGV.size() << "\n";
          errs() << "Args Aliased: " << AccessedArgs.size() << "\n";
        */
        return false;
    }




    bool doFinalization(Module &M) override{


        return false;

    }


    // We don't modify the program, so we preserve all analyses.
    void getAnalysisUsage(AnalysisUsage &AU) const override {

        AU.setPreservesAll();
        AU.addRequiredTransitive<AAResultsWrapperPass>();
        AU.addRequiredTransitive<GlobalsAAWrapperPass>();
        AU.addRequiredTransitive<CFLAndersAAWrapperPass>();
        AU.addRequiredTransitive<TypeBasedAAWrapperPass>();

        //assert(false && "getAnalysisUsage Called");
    }
  };

}
char ExperimentAnalysis::ID = 0;
INITIALIZE_PASS_BEGIN(ExperimentAnalysis, "ExperimentAnalysis", "Performs LLVM Analysis",false, false)
INITIALIZE_PASS_DEPENDENCY(AAResultsWrapperPass)
INITIALIZE_PASS_DEPENDENCY(GlobalsAAWrapperPass)
INITIALIZE_PASS_DEPENDENCY(CFLAndersAAWrapperPass)
INITIALIZE_PASS_END(ExperimentAnalysis, "ExperimentAnalysis", "Performs LLVM Analysis",false, false)


FunctionPass *llvm::createExperimentAnalysisPass(){
  DEBUG(errs() << "Hexbox Pass" <<"\n");
  return new ExperimentAnalysis();
}
