//===-- MCExperimentPrinterPass.cpp - Insert Thumb-2 IT blocks ------------------===//
//
//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.
//
//===----------------------------------------------------------------------===//
#define DEBUG_TYPE "mc-printer"
#include "ARM.h"
#include "ARMMachineFunctionInfo.h"
#include "Thumb2InstrInfo.h"
#include "llvm/ADT/SmallSet.h"
#include "llvm/ADT/Statistic.h"
#include "llvm/CodeGen/MachineFunctionPass.h"
#include "llvm/CodeGen/MachineInstr.h"
#include "llvm/CodeGen/MachineInstrBuilder.h"
#include "llvm/CodeGen/MachineInstrBundle.h"
#include "llvm/Support/Debug.h"
#include "llvm/Support/raw_ostream.h"
#include "json/json.h"
#include <fstream>
#include <iostream>
using namespace llvm;


static cl::opt<std::string> HexboxSizeData("hexbox-analysis-size",
                                  cl::desc("JSON File to write size info to"),
                                  cl::init("run.tmp"),cl::value_desc("filename"));
namespace {
  class MCExperimentPrinterPass : public MachineFunctionPass {
  public:
    static char ID;
    MCExperimentPrinterPass() : MachineFunctionPass(ID) {}

    Json::Value JsonRoot;
    bool runOnMachineFunction(MachineFunction &Fn) override{
        bool returnValue =false;
        MachineInstrBuilder MIB;
        unsigned numBytes = 0;
        Json::Value * JsonSize;
        //MachineOperand * MO;
        const GlobalValue * GV = nullptr;
        if ( HexboxSizeData.compare("-") == 0 ){
            return false;
        }


        const ARMBaseInstrInfo &TII =
            *static_cast<const ARMBaseInstrInfo *>(Fn.getSubtarget().getInstrInfo());
        DEBUG(errs()<<"Function: "<<Fn.getName() <<"\n");
        DEBUG(errs() << "---------------------------------------------------------\n");
        for (MachineBasicBlock &BB :Fn){
            SmallVector<MachineInstr *,16> DelInst;
            for(MachineInstr     &MI: BB){
                GV = nullptr;
                auto  I = std::next(MI.getIterator());
                auto DbgLoc = MI.getDebugLoc();

                //errs() << "Debug Loc: ";
                //DbgLoc.dump();
                switch(MI.getOpcode()){
                case ARM::HEXBOX_tBL:

                    loadAddrIntoLr(MIB,BB,I,TII,MI);
                    addCompartmentEntry(MIB,BB,I,TII,MI);
                    DelInst.push_back(&MI);
                    returnValue= true;
                break;
                case ARM::HEXBOX_tBLXr:
                    //errs() <<"Found HEXBOX_BLXr: " <<MI.getOpcode()<< "\n";
                    //MI.dump();

                    movRegToLR(MIB,BB,I,TII,MI);
                    addCompartmentEntry(MIB,BB,I,TII,MI);
                    DelInst.push_back(&MI);
                    returnValue = true;
                    break;

                }

                /* Replace returns on entry functions*/
                if (Fn.getFunction()->hasFnAttribute("HexboxEntry")){
                   if (MI.isReturn()){

                        switch (MI.getOpcode()){
                        case ARM::t2LDMIA_RET:
                            MIB = BuildMI(BB,I,DbgLoc,TII.get(ARM::t2LDMIA_UPD));
                            for (MachineOperand PopOp :MI.operands()){
                                if(PopOp.isReg()){
                                    if (PopOp.getReg()==ARM::PC){
                                        PopOp.setReg(ARM::LR);
                                    }
                                    MIB.addOperand(PopOp);
                                }

                            }
                            break;
                        case ARM::tPOP_RET: //Thumb can only pop lower 8 regs and PC
                            //Note this promotes thumb1 instruction to a thumb2
                            //which will break systems without thumb2
                            //errs() << "------------------ARM::tPOP_RET---------\n";
                            //MI.dump();
                            MIB = BuildMI(BB,I,DbgLoc,TII.get(ARM::t2LDMIA_UPD),ARM::SP);

                            MIB.addReg(ARM::SP);
                            MIB.addOperand(MI.getOperand(0));
                            MIB.addOperand(MI.getOperand(1));
                            for (unsigned i = 0; i< MI.getNumOperands();i++){
                                MachineOperand PopOp = MI.getOperand(i);
                                if(PopOp.isReg() && PopOp.getReg()!=ARM::NoRegister){
                                    if (PopOp.getReg()==ARM::PC){
                                        PopOp.setReg(ARM::LR);
                                    }
                                    MIB.addOperand(PopOp);
                                }
                                //MIB->dump();
                            }
                            break;
                        case ARM::tBX_RET:

                            //This assumes that only LR is used. IE return address
                            // already in LR
                            //Can just replace with SVC
                            break;
                        case ARM::tBX_RET_vararg:{

                            unsigned Reg =ARM::PC; //It can't be this reg
                            for (MachineOperand & Op : MI.operands()){
                                if (Op.isReg()){
                                    Reg = Op.getReg();
                                    break;
                                }
                            }
                            assert(Reg==ARM::PC && "Didn't Find Reg in replacing Vararg return in Hexbox");
                            if (Reg != ARM::LR){
                                MIB = BuildMI(BB,I,DbgLoc,TII.get(ARM::tMOVr),ARM::LR);//This may not be possible in thumb may require thumb2 to mov into LR
                                MIB.addReg(Reg);
                                AddDefaultPred(MIB);
                            }
                            break;
                        }
                        default:
                            assert(false && "Unhandled Return in Hexbox Entry function");
                        }
                        returnValue=true;
                        MIB = BuildMI(BB,I,DbgLoc,TII.get(ARM::tSVC));
                        MIB.addImm(101);
                        AddDefaultPred(MIB);
                        DelInst.push_back(&MI);
                    }
                }

                numBytes += MI.getDesc().getSize();
                //.dump();
            }

            // Delete Instructions that were replaced
            for (auto MI_del :DelInst){
                BB.remove_instr(MI_del);
            }
        }
        JsonRoot[Fn.getName().str()];
        JsonSize = &(JsonRoot[Fn.getName().str()]["Size"]);
        (*JsonSize) = numBytes;


        return returnValue;
    }

    void movRegToLR(MachineInstrBuilder & MIB,
                    MachineBasicBlock &BB,
                    MachineBasicBlock::iterator I,
                    const ARMBaseInstrInfo &TII,
                    MachineInstr & MI){
        auto DbgLoc = MI.getDebugLoc();

        MIB = BuildMI(BB,I,DbgLoc,TII.get(ARM::tMOVr), ARM::LR);
        MIB.addOperand(MI.getOperand(2));
        AddDefaultPred(MIB);
        //MIB->dump();

    }

    void loadAddrIntoLr(MachineInstrBuilder & MIB,
                        MachineBasicBlock & BB,
                        MachineBasicBlock::iterator I,
                        const ARMBaseInstrInfo &TII,
                        MachineInstr &MI){


        auto DbgLoc = MI.getDebugLoc();

        MIB = BuildMI(BB,I,DbgLoc,TII.get(ARM::t2MOVi16), ARM::LR);
        MIB.addGlobalAddress(MI.getOperand(2).getGlobal(),0,1);
        AddDefaultPred(MIB);

        //movt lr
        MIB = BuildMI(BB,I,DbgLoc,TII.get(ARM::t2MOVTi16), ARM::LR);
        MIB.addReg(ARM::LR);
        MIB.addGlobalAddress(MI.getOperand(2).getGlobal(),0,2);
        AddDefaultPred(MIB);
    }

    void addCompartmentEntry(MachineInstrBuilder & MIB,
                             MachineBasicBlock &BB,
                             MachineBasicBlock::iterator I,
                             const ARMBaseInstrInfo &TII,
                             MachineInstr & MI){
        const GlobalValue * GV = nullptr;

        auto DbgLoc = MI.getDebugLoc();
        //SVC 100
        MIB = BuildMI(BB,I,DbgLoc,TII.get(ARM::tSVC));
        MIB.addImm(100);
        AddDefaultPred(MIB);
        //Data

        MIB = BuildMI(BB,I,DbgLoc,TII.get(ARM::INLINEASM));
        //MI.dump();
        GV = MI.getOperand(3).getGlobal();
        if (GV){

            std::string *cmd = new std::string(".long " +GV->getName().str());
            DEBUG(errs() << "Adding Metadata to code\n");
            DEBUG(errs() << cmd);
            MIB.addOperand(MachineOperand::CreateES(cmd->c_str()));
            //MIB.addOperand(MachineOperand::CreateES(".long 0xDEEEDEEE"));

        }else{
            assert(false && "Invalid Hexbox Metadata");
        }


        MIB.addOperand(MachineOperand::CreateImm(InlineAsm::AD_ATT));
    }


    bool doInitialization(Module &) override{
        if ( HexboxSizeData.compare("-") == 0 ){
            return false;
        }
        DEBUG(errs() <<"\n\n\nStarting Machine Instruction Replacement\n\n");
        return false;
    }

    bool doFinalization(Module &) override{
        if ( HexboxSizeData.compare("-") == 0 ){
            return false;
        }
        std::ofstream jsonFile;
        jsonFile.open(HexboxSizeData);
        jsonFile <<JsonRoot;
        jsonFile.close();
        return false;
    }

    StringRef getPassName() const override {
      return StringRef("Printer Pass For Experimentation");
    }

  
  };
  char MCExperimentPrinterPass::ID = 0;
}




/// createMCExperimentPrinterPass - Returns an instance of the Thumb2 IT blocks
/// insertion pass.
FunctionPass *llvm::createMCExperimentPrinterPass() {
  return new MCExperimentPrinterPass();
}


