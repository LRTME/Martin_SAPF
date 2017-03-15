/****************************************************************
* FILENAME:     PER_int.c
* DESCRIPTION:  periodic interrupt code
* AUTHOR:       Mitja Nemec
*
****************************************************************/
#include    "PER_int.h"
#include    "TIC_toc.h"

// generiranje �eljene vrednosti
float ref_counter = 0;
float ref_counter_freq = 10; // Hz
float ref_counter_cmpr = 0.025;

float ref_value = 0;
float ref_value_high = 0.85;
float ref_value_low = 0.05;

// za oceno obremenjenosti CPU-ja
float   cpu_load  = 0.0;
long    interrupt_cycles = 0;

// temperatura procesorja
float	cpu_temp = 0.0;
float	napetost = 0.0;

// tokovi
float   IS = 0.0;
float   IF = 0.0;

float   IS_offset = 2048;
float   IF_offset = 2048;

float   IS_gain = (15.0 / 0.625 ) * (7.5 / 6.2) * (3.3 / 4096);
float   IF_gain = (25.0 / 0.625 ) * (7.5 / 6.2) * (3.3 / 4096);

long    current_offset_counter = 0;

// napetosti
float   u_ac = 0.0;

float   DEL_UDC = 0.0;
float   u_f = 0.0;
float   u_out = 0.0;

float   u_ac_offset = 2048.0;
float   DEL_UDC_offset = 2048.0;
float   u_f_offset = 2048.0;
float   u_out_offset = 2048.0;

float   u_ac_gain = ((1000 + 0.47) / (5 * 0.47)) * U_AC_CORR_F * (3.3 / 4096);
float   DEL_UDC_gain = ((200 + 1.8) / (5 * 1.8)) * DEL_UDC_CORR_F * (3.3 / 4096);
float   u_f_gain = ((200 + 1.8) / (5 * 1.8)) * (3.3 / 4096);
float   u_out_gain = ((1000 + 0.47) / (5 * 0.47)) * U_OUT_CORR_F * (3.3 / 4096);

// NTC
float beta_NTC = 3988;
float R_NTC25 = 5000;
float T_NTC25 = 298;
float V_NTC = 0.0;
float R_NTC = 0.0;
float T_NTC = 0.0;

// filtrirana napetost DC linka
DC_float    napetost_dc_f = DC_FLOAT_DEFAULTS;
float   DEL_UDC_filtered = 0.0;

// prvi harmonik in RMS vhodne omre�ne napetosti (u_ac)
DFT_float   u_ac_dft = DFT_FLOAT_DEFAULTS;
float   u_ac_rms = 0.0;
float   u_ac_form = 0.0;

// prvi harmonik in RMS izhodne napetosti (u_out)
DFT_float   u_out_dft = DFT_FLOAT_DEFAULTS;
float   u_out_rms = 0.0;
float   u_out_form = 0.0;

// regulacija napetosti enosmernega tokokroga
PID_float   DEL_UDC_reg = PID_FLOAT_DEFAULTS;
SLEW_float  DEL_UDC_slew = SLEW_FLOAT_DEFAULTS;

// regulacija omreznega toka
PID_float   IS_reg = PID_FLOAT_DEFAULTS;

// regulacija izhodne napetosti
PID_float   u_out_reg = PID_FLOAT_DEFAULTS;
SLEW_float  u_out_slew = SLEW_FLOAT_DEFAULTS;

// sinhronizacija na omre�je
float       sync_base_freq = SWITCH_FREQ;
PID_float   sync_reg    = PID_FLOAT_DEFAULTS;
float       sync_switch_freq = SWITCH_FREQ;
float       sync_grid_freq = ((SWITCH_FREQ/SAMPLING_RATIO)/SAMPLE_POINTS);
bool        sync_use = TRUE;

// samo za statistiko meritev
STAT_float  statistika = STAT_FLOAT_DEFAULTS;

// za oceno bremenskega toka
ABF_float   i_cap_abf = ABF_FLOAT_DEFAULTS;
float       IF_abf = 0.0;

// za oceno DC-link toka
ABF_float   i_cap_dc = ABF_FLOAT_DEFAULTS;
float       I_dc_abf = 0.0;

// za zakasnitev omreznega toka
DELAY_float i_grid_delay = DELAY_FLOAT_DEFAULTS;

// filtriranje izhoda ocene
DC_float    i_dc_f = DC_FLOAT_DEFAULTS;

// filtriranje meritve
DC_float    IF_f = DC_FLOAT_DEFAULTS;

// izbira ocene izhodnega toka
volatile enum   {Meas_out = 0, ABF_out, KF_out, None_out } IF_source = Meas_out;

// izbira ocene dc toka
volatile enum   {Meas_dc = 0, ABF_dc, KF_dc, None_dc, Power_out } I_dc_source = ABF_dc;

// izhodna moc
float   power_out = 0.0;

// temperatura hladilnika
float   temperatura = 0.0;

// prototipi funkcij
void get_electrical(void);
void input_bridge_control(void);
float NTC_temp(void);


// spremenljikva s katero �tejemo kolikokrat se je prekinitev predolgo izvajala
int interrupt_overflow_counter = 0;

/**************************************************************
* Prekinitev, ki v kateri se izvaja regulacija
**************************************************************/
#pragma CODE_SECTION(PER_int, "ramfuncs");
void interrupt PER_int(void)
{
    /* lokalne spremenljivke */
    
    // najprej povem da sem se odzzval na prekinitev
    // Spustimo INT zastavico casovnika ePWM1
    EPwm1Regs.ETCLR.bit.INT = 1;
    // Spustimo INT zastavico v PIE enoti
    PieCtrlRegs.PIEACK.all = PIEACK_GROUP3;
    
    // pozenem stoprico
    interrupt_cycles = TIC_time;
    TIC_start();

    // izracunam obremenjenost procesorja
    cpu_load = (float)interrupt_cycles / (CPU_FREQ/SAMPLE_FREQ);

    // povecam stevec prekinitev
    interrupt_cnt = interrupt_cnt + 1;
    if (interrupt_cnt >= SAMPLE_FREQ)
    {
        interrupt_cnt = 0;
    }

    // generiram spreenjljivo �eleno vrednost
    ref_counter = ref_counter + ref_counter_freq/SWITCH_FREQ;
    if (ref_counter >= 1.0)
    {
        ref_counter = 0;
    }

    // stopnicasta zeljena vrednost
    if (ref_counter > ref_counter_cmpr)
    {
        ref_value = ref_value_low;
    }
    else
    {
        ref_value = ref_value_high;
    }

    // pocakam da ADC konca s pretvorbo
   // ADC_wait();

    //napetost = ADC_B3/4096.0;

    // izracun napetosti, tokov in temperature hladilnika
    get_electrical();

    // naracunam temperaturo
    //cpu_temp = GetTemperatureC(ADC_TEMP);

    // spavim vrednosti v buffer za prikaz
    DLOG_GEN_update();
    
    /* preverim, �e me slu�ajno �aka nova prekinitev.
       �e je temu tako, potem je nekaj hudo narobe
       saj je �as izvajanja prekinitve predolg
       vse skupaj se mora zgoditi najmanj 10krat,
       da re�emo da je to res problem
    */
    if (EPwm1Regs.ETFLG.bit.INT == TRUE)
    {
        // povecam stevec, ki steje take dogodke
        interrupt_overflow_counter = interrupt_overflow_counter + 1;
        
        // in ce se je vse skupaj zgodilo 10 krat se ustavim
        // v kolikor uC krmili kak�en resen HW, potem mo�no
        // proporo�am lep�e "hendlanje" takega dogodka
        // beri:ugasni mo�nostno stopnjo, ...
        if (interrupt_overflow_counter >= 10)
        {
            asm(" ESTOP0");
        }
    }
    
    // stopam
    TIC_stop();
	PCB_WD_KICK_int();

}   // end of PWM_int

/**************************************************************
* Funckija, ki pripravi vse potrebno za izvajanje
* prekinitvene rutine
**************************************************************/
void PER_int_setup(void)
{
    // inicializiram data logger
    dlog.mode = Single;
    dlog.auto_time = 1;
    dlog.holdoff_time = 1;

    dlog.prescalar = 1;                		// store every  sample

    dlog.slope = Negative;
    dlog.trig = &ref_counter;
    dlog.trig_value = 0.5;

    dlog.iptr1 = &ref_counter;
    dlog.iptr2 = &cpu_temp;
    dlog.iptr3 = &napetost;

    // Pro�enje prekinitve
    EPwm1Regs.ETSEL.bit.INTSEL = ET_CTR_ZERO;    //spro�i prekinitev na periodo
    EPwm1Regs.ETPS.bit.INTPRD = ET_1ST;         //ob vsakem prvem dogodku
    EPwm1Regs.ETCLR.bit.INT = 1;                //clear possible flag
    EPwm1Regs.ETSEL.bit.INTEN = 1;              //enable interrupt

    // registriram prekinitveno rutino
    EALLOW;
    PieVectTable.EPWM1_INT = &PER_int;
    EDIS;
    PieCtrlRegs.PIEACK.all = PIEACK_GROUP3;
    PieCtrlRegs.PIEIER3.bit.INTx1 = 1;
    IER |= M_INT3;
    // da mi prekinitev te�e  tudi v real time na�inu
    // (za razhor��evanje main zanke in BACK_loop zanke)
    SetDBGIER(M_INT3);
}

#pragma CODE_SECTION(get_electrical, "ramfuncs");
void get_electrical(void)
{
    static float   IS_offset_calib = 0;
    static float   IF_offset_calib = 0.0;
    static float   u_ac_offset_calib = 0.0;
    static float   DEL_UDC_offset_calib = 0.0;
    static float   u_f_offset_calib = 0.0;
    static float   u_out_offset_calib = 0.0;

    // pocakam da ADC konca s pretvorbo
    ADC_wait();
    // poberem vrednosti iz AD pretvornika

    // kalibracija preostalega toka
    if (   (start_calibration == TRUE)
        && (calibration_done == FALSE))
    {
        // akumuliram offset
        IS_offset_calib = IS_offset_calib + IS_adc;
        IF_offset_calib = IF_offset_calib + IF_adc;
        u_ac_offset_calib = u_ac_offset_calib + u_ac_adc;
        DEL_UDC_offset_calib = DEL_UDC_offset_calib + DEL_UDC_adc;
        u_f_offset_calib = u_f_offset_calib + u_f_adc;
        u_out_offset_calib = u_out_offset_calib + u_out_adc;

        // ko potece dovolj casa, sporocim da lahko grem naprej
        // in izracunam povprecni offset
        current_offset_counter = current_offset_counter + 1;
        if (current_offset_counter == (SAMPLE_FREQ * 1L))
        {
            calibration_done = TRUE;
            start_calibration = FALSE;
            IS_offset = IS_offset_calib / (SAMPLE_FREQ*1L);
            IF_offset = IF_offset_calib / (SAMPLE_FREQ*1L);
            u_ac_offset = u_ac_offset_calib / (SAMPLE_FREQ*1L);
            DEL_UDC_offset = DEL_UDC_offset_calib / (SAMPLE_FREQ*1L);
            u_f_offset = u_f_offset_calib / (SAMPLE_FREQ*1L);
            u_out_offset = u_out_offset_calib / (SAMPLE_FREQ*1L);
        }

        IS = 0.0;
        IF = 0.0;
        u_ac = 0.0;
        DEL_UDC = 0.0;
        u_f = 0.0;
        u_out = 0.0;
    }
    else
    {
        IS = IS_gain * (IS_adc - IS_offset);
        IF = IF_gain * (IF_adc - IF_offset);
        u_ac = u_ac_gain * (u_ac_adc - u_ac_offset);
        DEL_UDC = DEL_UDC_gain * (DEL_UDC_adc - DEL_UDC_offset);
        u_f = u_f_gain * (u_f_adc - u_f_offset);
        u_out = u_out_gain * (u_out_adc - u_out_offset);
    }

    // temperatura hladilnika
    temperatura = NTC_temp();

    // porcunam DFT napetosti
    // vhodna omre�na napetost - u_ac
    u_ac_dft.In = u_ac;
    DFT_FLOAT_MACRO(u_ac_dft);

    // izhodna napetost - u_out
    u_out_dft.In = u_out;
    DFT_FLOAT_MACRO(u_out_dft);

    // nara�unam amplitudo omre�ne napetosti - u_ac
    u_ac_rms = ZSQRT2 * sqrt(u_ac_dft.SumA * u_ac_dft.SumA + u_ac_dft.SumB *u_ac_dft.SumB);

    // normiram, da dobim obliko
    u_ac_form = u_ac_dft.Out / (u_ac_rms * SQRT2);

    // nara�unam amplitudo izhodne napetosti - u_out
    u_out_rms = ZSQRT2 * sqrt(u_out_dft.SumA * u_out_dft.SumA + u_out_dft.SumB *u_out_dft.SumB);

    // normiram, da dobim obliko
    u_out_form = u_out_dft.Out / (u_out_rms * SQRT2);


    // filtriram DC link napetost
    napetost_dc_f.In = DEL_UDC;
    DC_FLOAT_MACRO(napetost_dc_f);
    DEL_UDC_filtered = napetost_dc_f.Mean;

    // izracunam kaksna moc je na izhodu filtra
    power_out = u_f * IF;

    // ocena izhodnega toka z ABF
   // i_cap_abf.u_cap_measured = u_f;
   // ABF_float_calc(&i_cap_abf);
   // IF_abf = -i_cap_abf.i_cap_estimated + (tok_bb1 + tok_bb2);

    // zakasnim IS
    i_grid_delay.in = IS * IS_reg.Out;
    DELAY_FLOAT_CALC(i_grid_delay);

    // ocena dc toka z ABF
    i_cap_dc.u_cap_measured = DEL_UDC;
    ABF_float_calc(&i_cap_dc);

    // se filtriram
    i_dc_f.In = -i_cap_dc.i_cap_estimated - i_grid_delay.out;
    DC_FLOAT_MACRO(i_dc_f);
    I_dc_abf = i_dc_f.Mean;

    // filtriram tudi meritev toka
    IF_f.In = IF;
    DC_FLOAT_MACRO(IF_f);

    // statistika
    statistika.In = DEL_UDC;
    STAT_FLOAT_MACRO(statistika);
}

#pragma CODE_SECTION(NTC_temp, "ramfuncs");
float NTC_temp(void)
{
	V_NTC = M_TEMP_adc * (3.3/4096.0);
	R_NTC = 5100 * ((5/V_NTC) - 1);
	T_NTC = (T_NTC25 * beta_NTC)/(beta_NTC - T_NTC25 * log(R_NTC25/R_NTC)) - 273;

	return T_NTC;
}

#pragma CODE_SECTION(input_bridge_control, "ramfuncs");
void input_bridge_control(void)
{
    // regulacija deluje samo v teh primerih
    if (   (state == Standby)
        || (state == Enable)
        || (state == Working)
        || (state == Disable))
    {
        // najprej zapeljem zeleno vrednost po rampi
        SLEW_FLOAT_CALC(DEL_UDC_slew)

        // izvedem napetostni regulator
        DEL_UDC_reg.Ref = DEL_UDC_slew.Out;
        DEL_UDC_reg.Fdb = DEL_UDC_filtered;
        // izberem vir direktne krmilne veje
        // samo v primeru testiranja vhodnega pretvornika, ko je tok enosmernega
        // tokokroga peljan �ez tokovni senzor na izhodu
        if (IF_source == Meas_dc)
        {
            DEL_UDC_reg.Ff = IF_f.Mean * DEL_UDC_filtered * SQRT2 / u_ac_rms;
        }
        // privzeto uporabim ABF za oceno DC toka in posledi�no feedforward
        if (I_dc_source == ABF_dc)
        {
            DEL_UDC_reg.Ff = I_dc_abf * DEL_UDC_filtered * SQRT2 / u_ac_rms;
        }
        // brez direktne krmilne veje
        if (I_dc_source == None_dc)
        {
            u_out_reg.Ff = 0.0;
        }
        // ocena preko izhodne mo�i
        if (I_dc_source == Power_out)
        {
            DEL_UDC_reg.Ff = power_out * SQRT2 / u_ac_rms;
        }

        PID_FLOAT_CALC(DEL_UDC_reg);

        // izvedem tokovni regulator
        // tega bi veljalo zamenjati za PR regulator
        // ampak samo v primeru ko se sinhroniziram na omre�je
        IS_reg.Ref = -DEL_UDC_reg.Out * u_ac_form;
        IS_reg.Fdb = IS;
        IS_reg.Ff = u_ac/DEL_UDC;
        PID_FLOAT_CALC(IS_reg);

        // posljem vse skupaj na mostic
        FB_update(IS_reg.Out);
    }
    // sicer pa nicim integralna stanja
    else
    {
        DEL_UDC_reg.Ui = 0.0;
        IS_reg.Ui = 0.0;
        FB_update(0.0);
    }
}

