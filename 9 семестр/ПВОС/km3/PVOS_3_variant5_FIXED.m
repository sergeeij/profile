%% PRACTICAL TASK 3 - VARIANT 5
% Matched filtering of an LFM radio signal.
% Based on pvos_practice_2.m + pvos_practice_3.m from the teacher.
% Signal path: LFM -> real RF -> 10-bit ADC -> complex demodulator
% -> CIC decimator -> CIC compensation FIR -> matched filter (fftfilt).
% All calculations AFTER ADC are double; the ADC still quantizes to 10 bits.
clear; close all; clc;
rng(5);                              % Reproducible noise

%% 1. Parameters (variant 5)
fs = 150e6;                         % ADC sampling frequency, Hz
fsv = 15e6;                         % Frequency after decimation, Hz
fc = 180e6;                         % Input RF center frequency, Hz
fg = 180e6;                         % NCO frequency, Hz
noba = 10;                          % ADC bits
nobg = 10;                          % NCO nominal bits (double mode here)
nobo = 14;                          % Output word reference from task 2
R = fs / fsv;                       % Decimation factor = 10
N = 8;                              % Number of CIC sections
bandwidth = fsv / 2 / 1.2;         % Limit used in task 2 = 6.25 MHz

% Parameters of the required symmetric rectangular-envelope LFM
length_test = R * ceil(2^17 / R);     % 131080; must be divisible by CIC factor R
pulse_base = 512;                   % Time-bandwidth product B
pulse_bw = 3e6;                     % Chirp bandwidth, Hz (within the passband)
pulse_width = pulse_base / pulse_bw;% Pulse length = 170.667 us
prf = 1 / (2 * pulse_width);        % Repeat period = 2 pulse widths
pulse_samples = round(pulse_width * fs);
delay_samples = 30000;              % Echo delay, 200 us
SNR = 50;                           % Active-pulse input SNR, dB
A = 0.70 * (2^(noba-1) - 1);       % RF amplitude, safely inside ADC span
signal_power = A^2 / 2;
noise_power = signal_power / 10^(SNR/10);

fprintf('Variant 5: fs = %.1f MHz, fsv = %.1f MHz, R = %g, nADC = %d\n', ...
        fs/1e6, fsv/1e6, R, noba);
fprintf('LFM: B = %d, BW = %.2f MHz, tau = %.3f us, PRF = %.3f Hz\n', ...
        pulse_base, pulse_bw/1e6, pulse_width*1e6, prf);
fprintf('Samples per pulse: ADC = %d, after decimation = %d\n', ...
        pulse_samples, round(pulse_width*fsv));

folder = 'Results_PVOS_3_Variant_5';
if ~exist(folder,'dir'), mkdir(folder); end

%% 2. LFM from the teacher's phased.LinearFMWaveform
% Two replicas are generated on exact ADC / post-decimation grids.
ref_rf = get_lfm(fs, pulse_width, prf, pulse_bw);
ref_bb = get_lfm(fsv, pulse_width, prf, pulse_bw);

% One echo at a known delay, surrounded by zeros
x_bb = complex(zeros(length_test,1));
ind = delay_samples + (1:length(ref_rf));
if ind(end) > length_test
    error('Pulse does not fit in length_test. Increase length_test.');
end
x_bb(ind) = ref_rf;

t = (0:length_test-1).' / fs;
signal = A * real(x_bb .* exp(1i*2*pi*fc*t));
noise = sqrt(noise_power) * randn(length_test,1);
in = signal + noise;                 % Real analog-equivalent input

fig = figure('Color','w','Position',[100 100 1400 650]);
plot((0:length(ref_bb)-1)/fsv*1e6,real(ref_bb),'LineWidth',1);
hold on;
plot((0:length(ref_bb)-1)/fsv*1e6,imag(ref_bb),'LineWidth',1);
grid on; xlabel('t, us'); ylabel('Amplitude, rel. units');
title('Reference LFM signal at video frequency');
legend('I','Q','Location','best');
save_plot(fig,folder,'Figure_01_LFM_reference');

fig = figure('Color','w','Position',[100 100 1400 650]);
plot(t*1e6,in,'LineWidth',0.7); grid on;
xlabel('t, us'); ylabel('ADC input, LSB');
title('Radio signal at ADC input: one delayed LFM pulse');
save_plot(fig,folder,'Figure_02_RF_input');

%% 3. ADC, double-precision NCO and complex quadrature demodulation
adc_signal = get_adc(in,noba);      % 10-bit saturating ADC, result double
nco_signal = get_nco(fg,t);         % Complex double exp(-j*2*pi*fg*t)
dem_signal = get_dem(adc_signal,nco_signal);

%% 4. CIC decimator and FIR compensation from practical task 2
% CIC requires input rows to be an integer multiple of R.
dem_signal = double(dem_signal(:));
assert(mod(numel(dem_signal),R)==0, ...
    'CIC input length must be a multiple of R');
CIC = dsp.CICDecimator(R,1,N);
cic_signal = double(step(CIC,dem_signal)) / (R^N);

% Same pass/stop specifications as the original task 2 script
fPass = bandwidth/2;               % 3.125 MHz
fStop = bandwidth/2 + 500e3;       % 3.625 MHz
passbandRipple = 0.1;              % dB
stopbandAttenuation = 60;          % dB
FIR = dsp.CICCompensationDecimator(CIC, ...
    'DecimationFactor',1, ...
    'PassbandFrequency',fPass, ...
    'PassbandRipple',passbandRipple, ...
    'StopbandAttenuation',stopbandAttenuation, ...
    'StopbandFrequency',fStop, ...
    'SampleRate',fsv, ...
    'DesignForMinimumOrder',true);

hFIR = double(impz(FIR));
hFIR = hFIR(:) / sum(hFIR);          % Unity DC gain, not max(hFIR)
fir_signal = filter(hFIR,1,double(cic_signal));
y = double(fir_signal(:));
t_out = (0:length(y)-1).' / fsv;

fig = figure('Color','w','Position',[100 100 1400 650]);
plot(t_out*1e6,abs(double(cic_signal)),'LineWidth',1); hold on;
plot(t_out*1e6,abs(y),'LineWidth',1);
grid on; xlabel('t, us'); ylabel('|signal|, rel. units');
title('Complex envelope after CIC and FIR compensation');
legend('CIC','CIC + FIR','Location','best');
save_plot(fig,folder,'Figure_03_CIC_FIR_envelopes');

% Spectrum after quadrature filtering: chirp must be within ±1.5 MHz
[fspec,aspec] = get_spectrum(y,fsv);
fig = figure('Color','w','Position',[100 100 1400 650]);
plot(fspec/1e6,20*log10(aspec/max(aspec)+eps),'LineWidth',1);
grid on; xlabel('f, MHz'); ylabel('Magnitude, dBc');
title('Spectrum of LFM signal after digital filtering');
xlim([-fsv/2 fsv/2]/1e6);
save_plot(fig,folder,'Figure_04_Baseband_spectrum');

%% 5. Matched-filter impulse response, from practical task 3
replica_time = flipud(conj(double(ref_bb(:))));
window_time = hamming(length(replica_time));
replica_time_w = replica_time .* window_time;

% Compare the THREE teacher methods; fftfilt is used in the main signal path.
mf_filter = filter(replica_time,1,y); % Direct FIR
nfft = 2^nextpow2(length(y)+length(replica_time)-1);
mf_fft_full = ifft(fft(y,nfft).*fft(replica_time,nfft));
mf_fft_full = mf_fft_full(1:length(y)); % LINEAR, not circular, convolution
mf_fftfilt = fftfilt(replica_time,y);  % Segmented fast linear convolution
mf_fftfilt_w = fftfilt(replica_time_w,y); % Hamming-weighted replica

maxErrFFTFilt = max(abs(mf_filter-mf_fftfilt))/max(abs(mf_filter));
maxErrFFT = max(abs(mf_filter-mf_fft_full))/max(abs(mf_filter));
[peakValue,peakIndex] = max(abs(mf_fftfilt));
[peakValueW,peakIndexW] = max(abs(mf_fftfilt_w));

fprintf('Relative error direct FIR vs fftfilt: %.3e\n', maxErrFFTFilt);
fprintf('Relative error direct FIR vs full FFT: %.3e\n', maxErrFFT);
fprintf('Matched-filter peak sample (unweighted): %d of %d\n', peakIndex,length(y));
fprintf('Measured peak time: %.3f us (includes filter delays)\n',t_out(peakIndex)*1e6);
fprintf('Reference echo delay: %.3f us\n',delay_samples/fs*1e6);

fig = figure('Color','w','Position',[100 100 1400 650]);
plot(t_out*1e6,abs(y)/max(abs(y)),'LineWidth',1); hold on;
plot(t_out*1e6,abs(mf_fftfilt)/peakValue,'LineWidth',1.3);
grid on; xlabel('t, us'); ylabel('Normalized magnitude');
title('Before and after matched filtering (fftfilt)');
legend('Before matched filtering','After matched filtering','Location','best');
save_plot(fig,folder,'Figure_05_Pulse_compression');

fig = figure('Color','w','Position',[100 100 1400 650]);
plot(t_out*1e6,20*log10(abs(mf_fftfilt)/peakValue+eps),'LineWidth',1.2);
hold on;
plot(t_out*1e6,20*log10(abs(mf_fftfilt_w)/peakValueW+eps),'LineWidth',1.2);
grid on; xlabel('t, us'); ylabel('Normalized magnitude, dB');
title('Matched-filter responses: with and without Hamming window');
legend('No window','Hamming window','Location','best');
ylim([-90 5]);
save_plot(fig,folder,'Figure_06_Matched_filter_windowing');

% Detailed examination of the main lobe and sidelobes
fig = figure('Color','w','Position',[100 100 1400 650]);
plot((t_out-t_out(peakIndex))*1e6,20*log10(abs(mf_fftfilt)/peakValue+eps),'LineWidth',1.2);
hold on;
plot((t_out-t_out(peakIndex))*1e6,20*log10(abs(mf_fftfilt_w)/peakValueW+eps),'LineWidth',1.2);
grid on; xlabel('Time relative to peak, us'); ylabel('Normalized magnitude, dB');
title('Main lobe and sidelobes of matched-filter response');
xlim([-12 12]); ylim([-70 5]);
legend('No window','Hamming window','Location','best');
save_plot(fig,folder,'Figure_07_Sidelobes_zoom');

fig = figure('Color','w','Position',[100 100 1400 650]);
plot(t_out*1e6,abs(mf_filter),'LineWidth',1.5); hold on;
plot(t_out*1e6,abs(mf_fftfilt),'--','LineWidth',1);
grid on; xlabel('t, us'); ylabel('|matched filter output|');
title('Matched filtering by direct FIR and fftfilt');
legend('filter','fftfilt','Location','best');
save_plot(fig,folder,'Figure_08_FIR_vs_fftfilt');

%% 6. Numeric results for the report
Results = table(pulse_base,pulse_bw,pulse_width,prf,fs,fsv,R,N, ...
    length(ref_bb),peakIndex,t_out(peakIndex),maxErrFFTFilt,maxErrFFT, ...
    'VariableNames',{'B','BW_Hz','PulseWidth_s','PRF_Hz','FsADC_Hz', ...
    'FsVideo_Hz','Decimation','CIC_sections','LFM_samples_video', ...
    'Peak_index','Peak_time_s','Relative_error_fftfilt','Relative_error_fft'});
disp(Results);
writetable(Results,fullfile(folder,'PVOS_3_variant5_results.csv'));
disp('READY: all .fig and .tiff files are in Results_PVOS_3_Variant_5');

%% LOCAL FUNCTIONS (the functional units have variable arguments)
function s = get_lfm(sampleRate,pulseWidth,prf,bw)
    w = phased.LinearFMWaveform( ...
        'SampleRate',sampleRate, ...
        'PulseWidth',pulseWidth, ...
        'PRF',prf, ...
        'SweepBandwidth',bw, ...
        'SweepInterval','Symmetric', ...
        'Envelope','Rectangular');
    frame = step(w);
    n = round(pulseWidth*sampleRate);
    s = double(frame(1:n));
    s = s(:);
end

function adc = get_adc(x,bits)
    % Original task-2 quantizing ADC, rewritten to return double.
    limit = 2^(bits-1);
    adc = min(max(round(double(x)),-limit),limit-1);
end

function nco = get_nco(fg,t)
    % The NCO has no additional amplitude/phase mismatch in task 3.
    nco = exp(-1i*2*pi*fg*double(t(:)));
end

function out = get_dem(adc,nco)
    out = double(adc(:)).*double(nco(:));
end

function [f,a] = get_spectrum(x,fs)
    x = double(x(:));
    L = length(x);
    s = fftshift(fft(x.*hann(L)));
    a = abs(s);
    f = (-floor(L/2):ceil(L/2)-1).' * fs / L;
end

function save_plot(fig,folder,name)
    set(fig,'Color','w');
    ax = findall(fig,'Type','axes');
    for kk = 1:length(ax)
        set(ax(kk),'FontName','Times New Roman','FontSize',16);
    end
    savefig(fig,fullfile(folder,[name '.fig']));
    print(fig,fullfile(folder,[name '.tiff']),'-dtiff','-r300');
end
