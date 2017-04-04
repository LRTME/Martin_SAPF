/****************************************************************
 * FILENAME:     BACK_loop.c
 * DESCRIPTION:  background code
 * AUTHOR:       Mitja Nemec
 *
 ****************************************************************/

#include "BACK_loop.h"

// deklaracije statičnih lokalnih spremenljivk

bool ENABLE_SW = FALSE;  			// pulz, ko pritisnemo na tipko ENABLE
bool RESET_SW = FALSE;  			// pulz, ko pritisnemo na tipko RESET

bool pulse_1000ms = FALSE;
bool pulse_500ms = FALSE;
bool pulse_100ms = FALSE;
bool pulse_50ms = FALSE;
bool pulse_10ms = FALSE;

// deklaracije zunanjih spremenljivk


// pototipi funkcij

void SW_detect(void);
void pulse_gen(void);

void standby_fcn(void);
void working_fcn(void);
void fault_sensed_fcn(void);
void fault_fcn(void);


/**************************************************************
* Funkcija, ki se izvaja v ozadju med obratovanjem
**************************************************************/
#pragma CODE_SECTION(BACK_loop, "ramfuncs");
void BACK_loop(void)
{
    // lokalne spremenljivke
    while (1)
    {
        // hendlanje komunikacije
        COMM_runtime();

        pulse_gen();
        SW_detect();

		/*	state machine	*/

		switch(state)
		{
		case Standby:
			standby_fcn();
			break;
		case Working:
			working_fcn();
			break;
		case Fault_sensed:
		    fault_sensed_fcn();
		    break;
		case Fault:
			fault_fcn();
			break;
		}

        asm(" NOP");

        // end of while(1)
	}
}// end of BACK_loop

void pulse_gen(void)
{
    static long interrupt_cnt_old_500ms = 0;
    static long interrupt_cnt_old_100ms = 0;
    static long interrupt_cnt_old_50ms = 0;
    static long interrupt_cnt_old_10ms = 0;
    static int  pulse_1000ms_cnt = 0;

    long delta_cnt_500ms;
    long delta_cnt_100ms;
    long delta_cnt_50ms;
    long delta_cnt_10ms;

    if ( (interrupt_cnt - interrupt_cnt_old_500ms) < 0)
    {
        interrupt_cnt_old_500ms = interrupt_cnt_old_500ms - (SAMPLE_FREQ);
    }

    if ( (interrupt_cnt - interrupt_cnt_old_100ms) < 0)
    {
        interrupt_cnt_old_100ms = interrupt_cnt_old_100ms - (SAMPLE_FREQ);
    }

    if ( (interrupt_cnt - interrupt_cnt_old_50ms) < 0)
    {
        interrupt_cnt_old_50ms = interrupt_cnt_old_50ms - (SAMPLE_FREQ);
    }

    if ( (interrupt_cnt - interrupt_cnt_old_10ms) < 0)
    {
        interrupt_cnt_old_10ms = interrupt_cnt_old_10ms - (SAMPLE_FREQ);
    }

    delta_cnt_500ms = interrupt_cnt - interrupt_cnt_old_500ms;
    delta_cnt_100ms = interrupt_cnt - interrupt_cnt_old_100ms;
    delta_cnt_50ms = interrupt_cnt - interrupt_cnt_old_50ms;
    delta_cnt_10ms = interrupt_cnt - interrupt_cnt_old_10ms;

    // generiranje pulza vsakih 10ms
    if (delta_cnt_10ms > ((SAMPLE_FREQ)/100))
    {
        pulse_10ms = TRUE;
        interrupt_cnt_old_10ms = interrupt_cnt;
    }
    else
    {
        pulse_10ms = FALSE;
    }

    // generiranje pulza vsakih 50ms
    if (delta_cnt_50ms > ((SAMPLE_FREQ)/50))
    {
        pulse_50ms = TRUE;
        interrupt_cnt_old_50ms = interrupt_cnt;
    }
    else
    {
        pulse_50ms = FALSE;
    }


    // generiranje pulza vsakih 100ms
    if (delta_cnt_100ms > ((SAMPLE_FREQ)/10))
    {
        pulse_100ms = TRUE;
        interrupt_cnt_old_100ms = interrupt_cnt;
    }
    else
    {
        pulse_100ms = FALSE;
    }

    // generiranje pulza vsakih 500ms
    if (delta_cnt_500ms > ((SAMPLE_FREQ)/2))
    {
        pulse_500ms = TRUE;
        interrupt_cnt_old_500ms = interrupt_cnt;
    }
    else
    {
        pulse_500ms = FALSE;
    }

    // stejem pulze po 100ms, da dobimo pulz 1s
    if (pulse_100ms == TRUE)
    {
        pulse_1000ms_cnt = pulse_1000ms_cnt + 1;
        if (pulse_1000ms_cnt == 10)
        {
            pulse_1000ms = TRUE;
            pulse_1000ms_cnt = FALSE;
        }
        else
        {
            pulse_1000ms = FALSE;
        }
    }
    // preverjanje da pulz traja samo eno iteracijo
    if ((pulse_100ms != TRUE) && (pulse_1000ms == TRUE))
    {
        pulse_1000ms = FALSE;
    }
}

void SW_detect(void)
{
    // lokalne spremenljivke
	//100ms debounce
    const int SW_ON_cnt_limit = 10;

    static int ENABLE_SW_cnt = 0;
    static int RESET_SW_cnt = 0;

    bool ENABLE_SW_new;
    bool RESET_SW_new;

    // scan every 10ms
    if (pulse_10ms == 1)
    {
        // preberem stanja tipk
        ENABLE_SW_new = PCB_SW_ENABLE();
        RESET_SW_new = PCB_SW_RESET();

        // ali smo pritisnili na tipko ENABLE
        // ce je tipka pritisnjena, stopaj koliko casa je prisitsnjena (debounce)
        if (ENABLE_SW_new == TRUE)
        {
            ENABLE_SW_cnt = ENABLE_SW_cnt + 1;
        }
        // ce ni pritisnjena resetiraj stevec
        else
        {
            ENABLE_SW_cnt = 0;
        }

        // ce je tipka pritisnjena dovolj casa, javi programu - samo enkrat
        if (ENABLE_SW_cnt == SW_ON_cnt_limit)
        {
            ENABLE_SW = !ENABLE_SW;
        }

        // ali smo pritisnili na tipko RESET
        // ce je tipka pritisnjena, stopaj koliko casa je prisitsnjena
        if (RESET_SW_new == TRUE)
        {
            RESET_SW_cnt = RESET_SW_cnt + 1;
        }
        // ce ni pritisnjena resetiraj stevec
        else
        {
            RESET_SW_cnt = 0;
        }

        // ce je tipka pritisnjena dovolj casa, javi programu - samo enkrat
        if (RESET_SW_cnt == SW_ON_cnt_limit)
        {
            RESET_SW = !RESET_SW;
        }
    }
    // da je pulz dolg res samo in samo eno iteracijo

}

void standby_fcn(void)
{
	PCB_LED_READY_on();

	if(ENABLE_SW == TRUE)
	{
		state = Working;
	}
}

void working_fcn(void)
{
	PCB_LED_WORKING_on();
	FB1_enable();

}

void fault_fcn(void)
{
    // pobrišem napako, in grem v standby
    if (RESET_SW == TRUE)
    {
        // resetiram MCU - preko WD-ja
    	PCB_LED_FAULT_off();
        EALLOW;
        WdRegs.WDCR.all = 0x0040;
        EDIS;
    }
    // signalizacija
    PCB_LED_FAULT_on();
}

void fault_sensed_fcn(void)
{
    // izklopim mostic
    FB1_disable();
    FB2_disable();

    // izklopim vse kontaktorjev
    PCB_relay1_off();
    PCB_relay2_off();
    PCB_relay3_off();

    //FLT_int_disable();

    if (fault_flags.fault_registered == FALSE)
    {
        fault_flags.fault_registered = TRUE;
    }
    // signalizacija
    PCB_LED_WORKING_off();
    PCB_LED_READY_off();

    state = Fault;
}
