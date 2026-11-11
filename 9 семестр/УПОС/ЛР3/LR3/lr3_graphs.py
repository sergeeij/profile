
# ЛР №3. Обработка измерений ВЧ усилителя
# Требуются: numpy, pandas, matplotlib
# Установка: pip install numpy pandas matplotlib

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

FOLDER = Path(__file__).resolve().parent
GRAPHS = FOLDER / "graphs"
GRAPHS.mkdir(exist_ok=True)

# True — показывать графики на экране
# False — только сохранять PNG
SHOW_PLOTS = True

plt.rcParams["font.family"] = "Times New Roman"
plt.rcParams["font.size"] = 12


# ==========================================================
# ОБЩИЕ ФУНКЦИИ
# ==========================================================

def load_csv(filename):
    path = FOLDER / filename

    if not path.exists():
        print(f"Нет файла {filename}")
        return pd.DataFrame()

    df = pd.read_csv(
        path,
        sep=";",
        dtype=str,
        encoding="utf-8-sig"
    )

    for col in df.columns:
        df[col] = pd.to_numeric(
            df[col].str.strip().str.replace(",", ".", regex=False),
            errors="coerce"
        )

    return df.dropna(how="all")


def save_results(df, filename):
    df.to_csv(
        FOLDER / filename,
        sep=";",
        decimal=",",
        index=False,
        encoding="utf-8-sig",
        float_format="%.4f"
    )
    print("Сохранена таблица:", filename)


def save_plot(filename):
    plt.tight_layout()
    plt.savefig(GRAPHS / filename, dpi=300)
    if not SHOW_PLOTS:
        plt.close()
    print("Сохранён график:", filename)


def graph(x, y, xlabel, ylabel, title, filename):
    plt.figure(figsize=(9, 5))
    plt.plot(x, y, "o-", linewidth=1.7, markersize=6)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(True, alpha=0.5)
    save_plot(filename)


# ==========================================================
# 1. АЧХ И ОБРАТНАЯ ПЕРЕДАЧА S12
# ==========================================================

print("\n1. АЧХ и S12")

a = load_csv("01_gain.csv")
gain = pd.DataFrame(columns=["f_MHz", "Kp_dB"])

if not a.empty:
    forward = a.dropna(
        subset=["f_MHz", "P_forward_dBm", "P_cal_dBm"]
    ).copy()

    if not forward.empty:
        forward["Kp_dB"] = (
            forward["P_forward_dBm"] -
            forward["P_cal_dBm"]
        )

        gain = (
            forward.groupby("f_MHz", as_index=False)["Kp_dB"]
            .mean()
            .sort_values("f_MHz")
        )

        graph(
            gain["f_MHz"],
            gain["Kp_dB"],
            "Частота, МГц",
            "Коэффициент усиления, дБ",
            "АЧХ усилителя",
            "01_gain.png"
        )

        save_results(gain, "result_01_gain.csv")

    reverse = a.dropna(
        subset=["f_MHz", "P_reverse_dBm", "P_reverse_cal_dBm"]
    ).copy()

    if not reverse.empty:
        reverse["S12_dB"] = (
            reverse["P_reverse_dBm"] -
            reverse["P_reverse_cal_dBm"]
        )

        reverse = reverse.sort_values("f_MHz")

        graph(
            reverse["f_MHz"],
            reverse["S12_dB"],
            "Частота, МГц",
            "S12, дБ",
            "Обратная передача усилителя",
            "02_reverse.png"
        )

        save_results(
            reverse[["f_MHz", "S12_dB"]],
            "result_02_reverse.csv"
        )



# ==========================================================
# 2. КОЭФФИЦИЕНТ ШУМА
# ==========================================================

print("\n2. Коэффициент шума")

n = load_csv("02_noise.csv")

if not n.empty and not gain.empty:

    n = n.dropna(
        subset=["f_MHz", "P_noise_dBm", "RBW_Hz", "IL2_dB"]
    ).copy()

    n = n.merge(gain, on="f_MHz", how="left")
    n = n.dropna(subset=["Kp_dB"])
    n = n[n["RBW_Hz"] > 0].copy()

    if not n.empty:

        # Формула из методички:
        # Кш = P + IL2 - (-174 + 10lg(RBW) + Kp)

        n["NF_dB"] = (
            n["P_noise_dBm"]
            + n["IL2_dB"]
            - (
                -174
                + 10 * np.log10(n["RBW_Hz"])
                + n["Kp_dB"]
            )
        )

        n = n.sort_values("f_MHz")

        graph(
            n["f_MHz"],
            n["NF_dB"],
            "Частота, МГц",
            "Коэффициент шума, дБ",
            "Коэффициент шума усилителя",
            "03_noise_figure.png"
        )

        save_results(n, "result_03_noise.csv")


# ==========================================================
# 3. ТОЧКА ДЕЦИБЕЛЬНОЙ КОМПРЕССИИ P1dB
# ==========================================================

print("\n3. Децибельная компрессия")

cal = load_csv("03_p1db_cal.csv")
p = load_csv("04_p1db.csv")

# Удаляем старые графики компрессии
for old in GRAPHS.glob("04_p1db_characteristic_*MHz.png"):
    old.unlink()

for old_name in [
    "05_op1db_vs_frequency.png",
    "05_ip1db_vs_frequency.png"
]:
    (GRAPHS / old_name).unlink(missing_ok=True)

if not cal.empty and not p.empty:

    cal = cal.dropna(
        subset=["f_MHz", "Pgen_cal_dBm", "P1_dBm", "P2_dBm"]
    )

    p = p.dropna(
        subset=["f_MHz", "Pgen_dBm", "P3_dBm"]
    )

    p = p.merge(cal, on="f_MHz", how="inner")

    # Потери входного тракта
    p["IL1_dB"] = p["Pgen_cal_dBm"] - p["P2_dBm"]

    # Потери выходного тракта
    p["IL2_dB"] = p["P2_dBm"] - p["P1_dBm"]

    # Измеренная выходная мощность усилителя
    p["Pout_dBm"] = p["P3_dBm"] + p["IL2_dB"] + p["IL1_dB"]

    # ВАЖНО:
    # Для построения характеристики берём Pgen,
    # а НЕ мощность непосредственно на входе усилителя.

    results = []
    all_points = []

    for f, one in p.groupby("f_MHz"):

        one = one.sort_values("Pgen_dBm").copy()

        if len(one) < 3:
            print(f"{f:g} МГц: недостаточно точек")
            continue

        # Малосигнальный участок — первые две точки
        gain_small = (
            one["Pout_dBm"].iloc[:2].to_numpy() -
            one["Pgen_dBm"].iloc[:2].to_numpy()
        )

        # Проверяем, что первые две точки действительно
        # дают примерно одинаковое усиление
        if abs(gain_small[1] - gain_small[0]) > 0.75:
            print(
                f"{f:g} МГц: малосигнальный участок "
                "неустойчив, P1dB не определяется"
            )
            continue

        k0 = gain_small.mean()

        # Линейная характеристика относительно Pgen
        one["Plinear_dBm"] = one["Pgen_dBm"] + k0

        # Величина компрессии
        one["compression_dB"] = (
            one["Plinear_dBm"] - one["Pout_dBm"]
        )

        one["Kp0_local_dB"] = k0

        x = one["Pgen_dBm"].to_numpy(dtype=float)
        y = one["Pout_dBm"].to_numpy(dtype=float)
        c = one["compression_dB"].to_numpy(dtype=float)

        pgen_1db = np.nan
        op1db = np.nan

        # Ищем первое пересечение компрессии 1 дБ
        for i in range(1, len(one)):

            if c[i - 1] <= 1 <= c[i] and c[i] != c[i - 1]:

                fraction = (
                    (1 - c[i - 1]) /
                    (c[i] - c[i - 1])
                )

                pgen_1db = (
                    x[i - 1] +
                    fraction * (x[i] - x[i - 1])
                )

                # Фактический уровень на выходе усилителя
                op1db = (
                    y[i - 1] +
                    fraction * (y[i] - y[i - 1])
                )

                break

        # --------------------------------------------------
        # ГРАФИК ДЛЯ ОТДЕЛЬНОЙ ЧАСТОТЫ
        # --------------------------------------------------

        plt.figure(figsize=(9, 5))

        plt.plot(
            one["Pgen_dBm"],
            one["Pout_dBm"],
            "o-",
            linewidth=1.8,
            label="Реальная характеристика"
        )

        plt.plot(
            one["Pgen_dBm"],
            one["Plinear_dBm"],
            "--",
            linewidth=1.7,
            label="Линейная характеристика"
        )

        if np.isfinite(pgen_1db):

            plt.scatter(
                pgen_1db,
                op1db,
                s=90,
                marker="x",
                color="red",
                zorder=5,
                label="Точка компрессии 1 дБ"
            )

            plt.axvline(
                pgen_1db,
                linestyle=":",
                color="red",
                alpha=0.7
            )

            plt.annotate(
                f"Pген = {pgen_1db:.2f} дБм\n"
                f"Pвых = {op1db:.2f} дБм",
                xy=(pgen_1db, op1db),
                xytext=(12, -35),
                textcoords="offset points",
                fontsize=10
            )

        plt.xlabel("Мощность генератора, дБм")
        plt.ylabel("Мощность на выходе усилителя, дБм")
        plt.title(
            f"Амплитудная характеристика, f = {f:g} МГц"
        )
        plt.grid(True, alpha=0.5)
        plt.legend()

        save_plot(f"04_p1db_characteristic_{f:g}MHz.png")

        results.append({
            "f_MHz": f,
            "Pgen_at_1dB_dBm": pgen_1db,
            "IP1dB_dBm": (
                pgen_1db - one["IL1_dB"].iloc[0]
                if np.isfinite(pgen_1db) else np.nan
            ),
            "OP1dB_dBm": op1db,
            "Kp0_dB": k0,
            "max_compression_dB": np.max(c)
        })

        all_points.append(one)

        if np.isfinite(pgen_1db):
            print(
                f"{f:g} МГц: Pген(1 дБ) = "
                f"{pgen_1db:.2f} дБм, "
                f"OP1dB = {op1db:.2f} дБм"
            )
        else:
            print(
                f"{f:g} МГц: компрессия 1 дБ "
                "в измеренном диапазоне не достигнута"
            )

    if all_points:
        save_results(
            pd.concat(all_points).sort_values(
                ["f_MHz", "Pgen_dBm"]
            ),
            "result_04_p1db_points.csv"
        )

    if results:

        res = pd.DataFrame(results).sort_values("f_MHz")

        save_results(res, "result_05_p1db.csv")

        found = res.dropna(
            subset=["Pgen_at_1dB_dBm", "OP1dB_dBm"]
        )

        if not found.empty:

            # ----------------------------------------------
            # ОТДЕЛЬНЫЙ ГРАФИК УРОВНЯ ГЕНЕРАТОРА ПРИ P1dB
            # ----------------------------------------------

            graph(
                found["f_MHz"],
                found["Pgen_at_1dB_dBm"],
                "Частота, МГц",
                "Мощность генератора, дБм",
                "Уровень генератора при компрессии 1 дБ",
                "05_ip1db_vs_frequency.png"
            )

            # ----------------------------------------------
            # ОТДЕЛЬНЫЙ ГРАФИК OP1dB
            # ----------------------------------------------

            graph(
                found["f_MHz"],
                found["OP1dB_dBm"],
                "Частота, МГц",
                "OP1dB, дБм",
                "Выходная точка компрессии 1 дБ",
                "05_op1db_vs_frequency.png"
            )


# ==========================================================
# 4. ИНТЕРМОДУЛЯЦИЯ ТРЕТЬЕГО ПОРЯДКА IP3
# ==========================================================

print("\n4. Интермодуляция IP3")

cal3 = load_csv("05_ip3_cal.csv")
im = load_csv("06_ip3.csv")

if not cal3.empty and not im.empty:

    cal3 = cal3.dropna(
        subset=["f_MHz", "P1_dBm", "P2_dBm"]
    )

    im = im.dropna(
        subset=["f_MHz", "P_tone_an_dBm", "P_IM3_an_dBm"]
    )

    im = im.merge(cal3, on="f_MHz", how="inner")

    if not gain.empty:
        im = im.merge(gain, on="f_MHz", how="left")
    else:
        im["Kp_dB"] = np.nan

    # Потери выходного тракта
    im["IL3_dB"] = im["P2_dBm"] - im["P1_dBm"]

    # Выходные мощности
    im["P_tone_out_dBm"] = (
        im["P_tone_an_dBm"] + im["IL3_dB"]
    )

    im["P_IM3_out_dBm"] = (
        im["P_IM3_an_dBm"] + im["IL3_dB"]
    )

    # Разница между основным тоном и IM3
    im["IMD3_dB"] = (
        im["P_tone_out_dBm"] -
        im["P_IM3_out_dBm"]
    )

    # Точки пересечения
    im["OIP3_dBm"] = (
        im["P_tone_out_dBm"] +
        im["IMD3_dB"] / 2
    )

    im["IIP3_dBm"] = (
        im["OIP3_dBm"] - im["Kp_dB"]
    )

    for f, one in im.groupby("f_MHz"):

        one = one.dropna(
            subset=["P_in_tone_dBm"]
        ).sort_values("P_in_tone_dBm")

        if len(one) < 2:
            continue

        x = one["P_in_tone_dBm"].to_numpy()
        y1 = one["P_tone_out_dBm"].to_numpy()
        y3 = one["P_IM3_out_dBm"].to_numpy()

        # Теоретические наклоны 1 и 3 дБ/дБ
        b1 = np.mean(y1 - x)
        b3 = np.mean(y3 - 3 * x)

        x_ip3 = (b1 - b3) / 2

        xs = np.linspace(
            min(x),
            max(max(x), x_ip3),
            150
        )

        plt.figure(figsize=(9, 5))

        plt.plot(x, y1, "o", label="Основной тон")
        plt.plot(x, y3, "s", label="Продукт IM3")

        plt.plot(
            xs,
            xs + b1,
            "--",
            label="Экстраполяция 1:1"
        )

        plt.plot(
            xs,
            3 * xs + b3,
            "--",
            label="Экстраполяция 3:1"
        )

        plt.scatter(
            x_ip3,
            x_ip3 + b1,
            marker="x",
            s=90,
            color="red",
            label="IP3 (экстраполяция)"
        )

        plt.xlabel("Входная мощность одного тона, дБм")
        plt.ylabel("Выходная мощность, дБм")
        plt.title(
            f"Интермодуляционные характеристики, {f:g} МГц"
        )
        plt.grid(True, alpha=0.5)
        plt.legend()

        save_plot(f"06_ip3_characteristic_{f:g}MHz.png")

    save_results(
        im.sort_values("f_MHz"),
        "result_06_ip3_points.csv"
    )

    summary = (
        im.groupby("f_MHz", as_index=False)[
            ["OIP3_dBm", "IIP3_dBm"]
        ]
        .mean()
        .sort_values("f_MHz")
    )

    graph(
        summary["f_MHz"],
        summary["OIP3_dBm"],
        "Частота, МГц",
        "OIP3, дБм",
        "Выходная IP3 от частоты",
        "07_oip3_vs_frequency.png"
    )

    valid_iip3 = summary.dropna(subset=["IIP3_dBm"])

    if not valid_iip3.empty:
        graph(
            valid_iip3["f_MHz"],
            valid_iip3["IIP3_dBm"],
            "Частота, МГц",
            "IIP3, дБм",
            "Входная IP3 от частоты",
            "08_iip3_vs_frequency.png"
        )

    save_results(summary, "result_07_ip3.csv")


# ==========================================================
# 5. КОЭФФИЦИЕНТЫ ОТРАЖЕНИЯ S11 И S22
# ==========================================================

print("\n5. Коэффициенты отражения")

r = load_csv("07_reflection_optional.csv")

if not r.empty:

    for port in ["in", "out"]:

        fields = [
            "f_MHz",
            f"P_open_{port}_dBm",
            f"P_ref_{port}_dBm"
        ]

        subset = r.dropna(subset=fields).copy()

        if subset.empty:
            continue

        tag = "S11" if port == "in" else "S22"

        subset[f"{tag}_dB"] = (
            subset[f"P_ref_{port}_dBm"] -
            subset[f"P_open_{port}_dBm"]
        )

        subset = subset.sort_values("f_MHz")

        graph(
            subset["f_MHz"],
            subset[f"{tag}_dB"],
            "Частота, МГц",
            f"{tag}, дБ",
            f"Коэффициент отражения {tag}",
            f"09_{tag.lower()}.png"
            if port == "in"
            else f"10_{tag.lower()}.png"
        )

        save_results(
            subset[["f_MHz", f"{tag}_dB"]],
            f"result_{tag.lower()}.csv"
        )


# ==========================================================
# ЗАВЕРШЕНИЕ
# ==========================================================

print("\nВСЕ ИЗМЕРЕНИЯ ОБРАБОТАНЫ")
print("Графики:", GRAPHS)

if SHOW_PLOTS and plt.get_fignums():
    plt.show()
