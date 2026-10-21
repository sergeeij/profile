import scipy.io as sio
import numpy as np
import matplotlib.pyplot as plt
import scipy.signal as signal
import psd

mat = sio.loadmat('test1_25p0.mat')

x = mat['pdin']
y = mat['pdout']

tx_freq = mat['tx_freq']
rx_freq = mat['rx_freq']

x = np.reshape(x, x.size)
y = np.reshape(y, y.size)

#tx_freq = float(np.reshape(tx_freq,1))
#rx_freq = float(np.reshape(rx_freq,1))
tx_freq = tx_freq.item()
rx_freq = rx_freq.item()

Fs = 245.76E6

(X, frq) = psd.psd_welch(x, 2048, signal.windows.blackmanharris(2048), 1024, Fs)
(Y, frq) = psd.psd_welch(y, 2048, signal.windows.blackmanharris(2048), 1024, Fs)

print("x:",len(x), " y:", len(y), " f_prd:", tx_freq, " f_prm:", rx_freq)
plt.figure(1)
plt.plot(frq/1E6, X, frq/1E6, Y)
plt.xlabel('freq, MHz')
plt.ylabel('PSD, dB/Hz')
plt.grid(True)
"""
---------------------------------------------------------------------
"""
# Шаг 1 Удалить постоянную составляющую смесителя приемника
DC = np.mean(y)
y = y - DC
print("DC:", DC)
(Y, frq) = psd.psd_welch(y, 2048, signal.windows.blackmanharris(2048), 1024, Fs)

plt.figure(2)
plt.plot(frq/1E6, X, frq/1E6, Y)
plt.title("После удаления постоянной составляющей")
plt.xlabel('freq, MHz')
plt.ylabel('PSD, dB/Hz')
plt.grid(True)

# Шаг 2 Скомпенсировать частотное смещение rx_freq и tx_freq

delta_f =rx_freq - tx_freq

n = np.arange(len(y))
y = y * np.exp(1j * 2 * np.pi * delta_f * n / Fs)

(Y, frq) = psd.psd_welch(y, 2048, signal.windows.blackmanharris(2048), 1024, Fs)

plt.figure(3)
plt.plot(frq/1E6, X, frq/1E6, Y)
plt.title("После компенсирование частотного смещения")
plt.xlabel('freq, MHz')
plt.ylabel('PSD, dB/Hz')
plt.grid(True)

# Шаг 3 Выравнивание данных во времени
plt.figure(4)
plt.subplot(1, 2, 1)
plt.plot(np.abs(x))
plt.plot(np.abs(y))
plt.title("До выравнивания")


cor = signal.correlate(y, x, mode='valid', method='fft')
delay = np.argmax(np.abs(cor))
y = y[delay:delay + len(x)]


plt.subplot(1, 2, 2)
plt.plot(np.abs(x))
plt.plot(np.abs(y))
plt.title("После выравнивания")
plt.grid(True)

# Шаг 4 Выравнивание по амплитуде и фазе
g = np.sum(np.conj(y) * x) / np.sum(np.abs(y) ** 2)
y = y * g

(Y, frq) = psd.psd_welch(y, 2048, signal.windows.blackmanharris(2048), 1024, Fs)
plt.figure(5)
plt.plot(frq/1E6, X, frq/1E6, Y)
plt.title("После компенсирование частотного смещения")
plt.xlabel('freq, MHz')
plt.ylabel('PSD, dB/Hz')
plt.grid(True)

#Шаг 5 Расчет сигнала ошибки (искажения в трактах)
e = x - y

(E, frq) = psd.psd_welch(e, 2048, signal.windows.blackmanharris(2048), 1024, Fs)

plt.figure(6)
plt.plot(frq/1E6, X, frq/1E6, Y, frq/1E6, E )
plt.title("После компенсирование частотного смещения")
plt.xlabel('freq, MHz')
plt.ylabel('PSD, dB/Hz')
plt.grid(True)
plt.show()