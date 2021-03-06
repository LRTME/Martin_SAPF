/****************************************************************
* FILENAME:     FLT_int.c
* DESCRIPTION:  fault handler
* AUTHOR:       Mitja Nemec
*
****************************************************************/
#include <FLT_int.h>
#include "globals.h"

/**************************************************************
* Prekinitev, ki se izvede, ko prime zascita ob napaki
**************************************************************/
#pragma CODE_SECTION(FLT_int_TZ1, "ramfuncs");
void interrupt FLT_int_TZ1(void)
{
    // onemogocim prekinitve, da ne padem zopet notri
    // ta prekinitev je ponovno omogocena, ko se ponovno zazene enota
    EALLOW;
    EPwm1Regs.TZEINT.bit.OST = 0;
    EDIS;

    // in Spustimo INT zastavico v TZ enoti
    EALLOW;
    EPwm1Regs.TZCLR.bit.INT = 1;
    EDIS;

    // ter javim, da je pri�lo do HW za��ite
    fault_flags.HW_trip = TRUE;
    state = Fault_sensed;
    // izklopim mostic
    FB1_disable();
    FB2_disable();

    // izklopim vse kontaktorje
    PCB_relay1_off();
    PCB_relay2_off();
    PCB_relay3_off();

    // detektiram vrsto napake
    if(PCB_CPLD_over_voltage() == FALSE)
    {
    	fault_flags.overvoltage_u_f = TRUE;
    }

	if(PCB_CPLD_over_current_supply() == FALSE)
	{
		fault_flags.overcurrent_IS = TRUE;
	}

	if(PCB_CPLD_over_current_filter() == FALSE)
	{
		fault_flags.overcurrent_IF = TRUE;
	}

    // Spustimo INT zastavico v PIE enoti
    PieCtrlRegs.PIEACK.all = PIEACK_GROUP2;
}   // end of FLT_int

#pragma CODE_SECTION(FLT_int_enable, "ramfuncs");
void FLT_int_enable(void)
{
    EALLOW;
    // spustim zastavice
    EPwm1Regs.TZCLR.bit.OST = 1;
    EPwm1Regs.TZCLR.bit.INT = 1;
    // omogocim prekinitev
    EPwm1Regs.TZEINT.bit.OST = 1;
    EDIS;
}

#pragma CODE_SECTION(FLT_int_disable, "ramfuncs");
void FLT_int_disable(void)
{
    EALLOW;
    // spustim zastavice
    EPwm1Regs.TZCLR.bit.OST = 1;
    EPwm1Regs.TZCLR.bit.INT = 1;
    // onemogocim prekinitev
    EPwm1Regs.TZEINT.bit.OST = 0;
    EDIS;
}

/**************************************************************
* funkcija, ki inicializira prekinitve in pripadajoce rutine
**************************************************************/
void FLT_int_setup(void)
{
	// registriram prekinitveno rutino
	EALLOW;

    // input pin setup (TZ1)
	InputXbarRegs.INPUT1SELECT = 19;

    // spustim zastavice
    EPwm1Regs.TZCLR.bit.OST = 1;
    EPwm1Regs.TZCLR.bit.INT = 1;

    PieVectTable.EPWM1_TZ_INT = &FLT_int_TZ1;
    // omogocim prekinitev
    EPwm1Regs.TZEINT.bit.OST = 1;
    EDIS;

    PieCtrlRegs.PIEIER2.bit.INTx1 = 1;
    IER |= M_INT2;
}
