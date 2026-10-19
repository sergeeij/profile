<Qucs Schematic 25.2.0>
<Properties>
  <View=-317,-307,1247,945,1.01526,0,150>
  <Grid=10,10,1>
  <DataSet=lab3_schema3.dat>
  <DataDisplay=lab3_schema3.dpl>
  <OpenDisplay=0>
  <Script=lab3_schema3.m>
  <RunScript=0>
  <showFrame=0>
  <FrameText0=Название>
  <FrameText1=Чертил:>
  <FrameText2=Дата:>
  <FrameText3=Версия:>
</Properties>
<Symbol>
</Symbol>
<Components>
  <Tr Tr1 1 40 280 -29 38 0 0 "1" 1>
  <GND * 1 180 340 0 0 0 0>
  <GND * 1 -10 310 0 0 0 0>
  <R R1 1 180 250 -90 -22 0 3 "2 kOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "european" 0>
  <R R2 1 280 310 15 -26 0 1 "2 kOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "european" 0>
  <Eqn Eqn1 5 790 50 -37 17 0 0 "fs=125e3" 1 "R=2k" 1 "C=636.6198p" 1 "Vout=out2.Vt-out1.Vt" 1 "yes" 0>
  <.TR TR1 1 370 -10 0 75 0 0 "lin" 1 "0" 1 "100u" 1 "2001" 1 "Trapezoidal" 0 "2" 0 "1 ns" 0 "1e-16" 0 "150" 0 "0.001" 0 "1 pA" 0 "1 uV" 0 "26.85" 0 "1e-3" 0 "1e-6" 0 "1" 0 "CroutLU" 0 "no" 0 "yes" 0 "0" 0>
  <C C2 1 280 250 17 -26 0 1 "636 pF" 1 "" 0 "neutral" 0>
  <C C1 1 180 310 -87 -28 1 1 "636 pF" 1 "" 0 "neutral" 0>
  <Vac V1 1 -10 280 -99 -31 0 1 "1" 1 "250 kHz" 1 "0" 0 "0" 0 "0" 0 "0" 0>
</Components>
<Wires>
  <70 310 70 340 "" 0 0 0 "">
  <70 340 180 340 "" 0 0 0 "">
  <70 220 70 250 "" 0 0 0 "">
  <70 220 180 220 "" 0 0 0 "">
  <-10 310 10 310 "" 0 0 0 "">
  <-10 250 10 250 "" 0 0 0 "">
  <180 220 280 220 "" 0 0 0 "">
  <180 340 280 340 "" 0 0 0 "">
  <180 280 180 280 "out1" 210 280 0 "">
  <280 280 280 280 "out2" 360 280 0 "">
  <70 220 70 220 "in" 90 170 0 "">
</Wires>
<Diagrams>
  <Rect -170 820 537 260 3 #c0c0c0 1 00 0 1e-05 1e-05 3e-05 1 -1.33405 0.5 1.21219 1 -1 0.5 1 315 0 225 1 0 0 "" "" "">
	<"in.Vt" #0055ff 0 3 0 0 0>
	  <Mkr 1.3e-05 126 -333 3 0 0>
	<"out1.Vt" #ff0000 0 3 0 0 0>
	  <Mkr 2.57e-05 451 -335 3 0 0>
	<"out2.Vt" #ff00ff 0 3 0 0 0>
	  <Mkr 2.47e-05 307 -336 3 0 0>
	<"Vout" #00ff00 0 3 0 0 0>
	  <Mkr 1.24e-05 -6 -338 3 0 0>
  </Rect>
</Diagrams>
<Paintings>
</Paintings>
