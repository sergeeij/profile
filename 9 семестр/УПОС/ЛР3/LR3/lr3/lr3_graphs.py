# ЛР №3 — обработка результатов измерений усилителя
# Заполняйте CSV-файлы, запускайте этот файл, графики появятся в папке graphs.
# Установка библиотек: pip install pandas numpy matplotlib

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

FOLDER = Path(__file__).resolve().parent
GRAPHS = FOLDER / "graphs"
GRAPHS.mkdir(exist_ok=True)
# True: после расчёта открыть интерактивные фигуры Matplotlib.
# False: только сохранить PNG в папку graphs.
SHOW_PLOTS = True
plt.rcParams["font.family"] = "Times New Roman"
plt.rcParams["font.size"] = 12


def load_csv(filename):
    """Читает CSV с разделителем ; и десятичной запятой или точкой."""
    path = FOLDER / filename
    data = pd.read_csv(path, sep=";", dtype=str, encoding="utf-8-sig")
    for name in data.columns:
        data[name] = pd.to_numeric(
            data[name].str.strip().str.replace(",", ".", regex=False),
            errors="coerce"
        )
    return data.dropna(how="all")


def graph(x, y, xlabel, ylabel, title, filename, label=None):
    plt.figure(figsize=(8, 5))
    plt.plot(x, y, "o-", label=label)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(True)
    if label is not None:
        plt.legend()
    plt.tight_layout()
    plt.savefig(GRAPHS / filename, dpi=200)
    if not SHOW_PLOTS:
        plt.close()
    print("  График:", filename)


def save_results(data, filename):
    data.to_csv(FOLDER / filename, sep=";", decimal=",", index=False,
                encoding="utf-8-sig", float_format="%.4f")
    print("  Таблица:", filename)


# -----------------------------------------------------------
# 1. КОЭФФИЦИЕНТ УСИЛЕНИЯ И ОБРАТНАЯ ПЕРЕДАЧА — 3.3.1
# -----------------------------------------------------------
print("\n1. АЧХ и обратная передача")
a = load_csv("01_gain.csv")
forward = a.dropna(subset=["f_MHz", "P_forward_dBm", "P_cal_dBm"]).copy()

if not forward.empty:
    forward["Kp_dB"] = forward["P_forward_dBm"] - forward["P_cal_dBm"]
    gain = forward.groupby("f_MHz", as_index=False)["Kp_dB"].mean().sort_values("f_MHz")
    graph(gain["f_MHz"], gain["Kp_dB"], "Частота, МГц", "Усиление, дБ",
          "АЧХ усилителя (S21)", "01_gain.png")
    save_results(gain, "result_01_gain.csv")
else:
    gain = pd.DataFrame(columns=["f_MHz", "Kp_dB"])
    print("  Нет данных для АЧХ: заполните 01_gain.csv")

reverse = a.dropna(subset=["f_MHz", "P_reverse_dBm", "P_reverse_cal_dBm"]).copy()
if not reverse.empty:
    reverse["S12_dB"] = reverse["P_reverse_dBm"] - reverse["P_reverse_cal_dBm"]
    reverse = reverse.sort_values("f_MHz")
    graph(reverse["f_MHz"], reverse["S12_dB"], "Частота, МГц",
          "Обратная передача S12, дБ", "Обратная передача усилителя", "02_reverse.png")
    save_results(reverse[["f_MHz", "S12_dB"]], "result_02_reverse.csv")
else:
    print("  Нет данных для обратной передачи (S12).")


# -----------------------------------------------------------
# 2. КОЭФФИЦИЕНТ ШУМА — 3.3.2
# -----------------------------------------------------------
print("\n2. Коэффициент шума")
(FOLDER / "result_03_noise.csv").unlink(missing_ok=True)
(GRAPHS / "03_noise_figure.png").unlink(missing_ok=True)
n = load_csv("02_noise.csv")
n = n.dropna(subset=["f_MHz", "P_noise_dBm", "RBW_Hz", "IL2_dB"])

if not n.empty and not gain.empty:
    n = n.merge(gain, on="f_MHz", how="left")
    n = n.dropna(subset=["Kp_dB"]).copy()
    missing_background = n["P_analyzer_dBm"].isna().sum()
    if missing_background:
        print(f"  Для {missing_background} частот не измерен фон анализатора; "
              "NF для них не рассчитывается.")
    n = n.dropna(subset=["P_analyzer_dBm"]).copy()
    n = n[n["RBW_Hz"] > 0].copy()
    if not n.empty:
        # -174 дБм/Гц — тепловая опора при 290 K, НЕ фон анализатора.
        # Из суммарной мощности вычитаем фон в линейной шкале.
        n["above_background_dB"] = n["P_noise_dBm"] - n["P_analyzer_dBm"]
        n["P_amp_at_analyzer_dBm"] = np.nan
        valid = n["above_background_dB"] > 0
        n.loc[valid, "P_amp_at_analyzer_dBm"] = (
            n.loc[valid, "P_noise_dBm"]
            + 10 * np.log10(1 - 10 ** (-n.loc[valid, "above_background_dB"] / 10))
        )
        n["NF_dB"] = n["P_amp_at_analyzer_dBm"] + n["IL2_dB"] - (
            -174 + 10 * np.log10(n["RBW_Hz"]) + n["Kp_dB"]
        )
        for _, row in n.iterrows():
            difference = row["above_background_dB"]
            if difference <= 0:
                print(f"  {row['f_MHz']:g} МГц: шум не выше фона; NF не определяется.")
            elif difference < 10:
                print(f"  {row['f_MHz']:g} МГц: превышение фона всего "
                      f"{difference:.1f} дБ; NF лишь предварительный.")
        n = n.sort_values("f_MHz")
        reliable = n[n["above_background_dB"] >= 10]
        if not reliable.empty:
            graph(reliable["f_MHz"], reliable["NF_dB"], "Частота, МГц", "NF, дБ",
                  "Коэффициент шума (только точки ≥10 дБ над фоном)",
                  "03_noise_figure.png")
        save_results(n, "result_03_noise.csv")
    else:
        print("  Нет измеренного фона для расчёта NF.")
else:
    print("  Нет данных или не заполнена АЧХ на тех же частотах.")


# -----------------------------------------------------------
# 3. ТОЧКА КОМПРЕССИИ P1dB — 3.3.3
# -----------------------------------------------------------
print("\n3. Точка децибельной компрессии")
(FOLDER / "result_04_p1db_points.csv").unlink(missing_ok=True)
(FOLDER / "result_05_p1db.csv").unlink(missing_ok=True)
(FOLDER / "result_05_p1db_status.csv").unlink(missing_ok=True)
(GRAPHS / "05_op1db_vs_frequency.png").unlink(missing_ok=True)
for old_graph in GRAPHS.glob("04_p1db_characteristic_*MHz.png"):
    old_graph.unlink()
cal = load_csv("03_p1db_cal.csv").dropna(
    subset=["f_MHz", "Pgen_cal_dBm", "P1_dBm", "P2_dBm"])
p = load_csv("04_p1db.csv").dropna(subset=["f_MHz", "Pgen_dBm", "P3_dBm"])

if not cal.empty and not p.empty:
    p = p.merge(cal, on="f_MHz", how="inner")
    if not gain.empty:
        p = p.merge(gain, on="f_MHz", how="left")
    else:
        p["Kp_dB"] = np.nan

    # Pgen — установка генератора; именно её показываем на оси графика.
    # Pin — физическая мощность на входе усилителя после входного тракта.
    # Pout — физическая мощность на выходе усилителя до выходного тракта.
    # IL1 не прибавляется к Pout: это потери ДО усилителя.
    p["IL1_dB"] = p["Pgen_cal_dBm"] - p["P2_dBm"]
    p["IL2_dB"] = p["P2_dBm"] - p["P1_dBm"]
    p["Pin_dBm"] = p["Pgen_dBm"] - p["IL1_dB"]
    p["Pout_dBm"] = p["P3_dBm"] + p["IL2_dB"]

    results_p1db = []
    processed_points = []
    status_rows = []
    for f, one in p.groupby("f_MHz"):
        one = one.sort_values("Pgen_dBm").copy()
        print(f"  {f:g} МГц: потери до входа {one['IL1_dB'].iloc[0]:.2f} дБ, "
              f"от выхода до анализатора {one['IL2_dB'].iloc[0]:.2f} дБ.")
        if len(one) < 2:
            print(f"  {f:g} МГц: для P1dB нужно хотя бы две точки.")
            status_rows.append([f, len(one), one["Pgen_dBm"].max(),
                                np.nan, np.nan, "Недостаточно точек"])
            continue
        # Линейный участок берём из ЭТОЙ серии, а не из отдельной АЧХ:
        # разные калибровки могут сдвинуть усиление на несколько дБ.
        small_signal_gains = (
            one["Pout_dBm"].iloc[:2] - one["Pin_dBm"].iloc[:2]
        )
        baseline_ok = abs(small_signal_gains.iloc[1] - small_signal_gains.iloc[0]) <= 0.75
        if baseline_ok:
            k0 = small_signal_gains.mean()
            one["Kp0_local_dB"] = k0
            one["Plinear_dBm"] = one["Pin_dBm"] + k0
            one["compression_dB"] = one["Plinear_dBm"] - one["Pout_dBm"]
        else:
            print(f"  {f:g} МГц: первые две точки расходятся по усилению более чем "
                  "на 0.75 дБ; малосигнальная линия и P1dB не определены.")
            one["Kp0_local_dB"] = np.nan
            one["Plinear_dBm"] = np.nan
            one["compression_dB"] = np.nan
        processed_points.append(one)

        crossing = None
        if baseline_ok:
            # Пересечение ищем по установкам генератора; сдвиг на IL1
            # не меняет величину компрессии.
            x = one["Pgen_dBm"].to_numpy(dtype=float)
            c = one["compression_dB"].to_numpy(dtype=float)
            for i in range(1, len(one)):
                if c[i-1] <= 1 <= c[i] and c[i] != c[i-1]:
                    pgen1 = x[i-1] + (1 - c[i-1]) * (x[i]-x[i-1]) / (c[i]-c[i-1])
                    ip1 = pgen1 - one["IL1_dB"].iloc[0]
                    op1 = ip1 + k0 - 1
                    crossing = (pgen1, op1)
                    results_p1db.append([f, pgen1, ip1, op1, k0])
                    break
            if crossing is None:
                print(f"  {f:g} МГц: точка компрессии 1 дБ не найдена. "
                      "Добавьте точки около изгиба.")

        status_rows.append([
            f, len(one), one["Pgen_dBm"].max(),
            one["compression_dB"].max() if baseline_ok else np.nan,
            crossing[1] if crossing is not None else np.nan,
            "P1dB найдена" if crossing is not None else
            ("1 дБ не достигнут" if baseline_ok else "Нет устойчивой опоры")
        ])

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(one["Pgen_dBm"], one["Pout_dBm"], "o-", label="Измеренная")
        if baseline_ok:
            ax.plot(one["Pgen_dBm"], one["Plinear_dBm"], "--",
                    label=f"Линейная (усиление {k0:.2f} дБ)")
        if crossing is not None:
            ax.plot(crossing[0], crossing[1], "r*", markersize=12,
                    label=f"P1dB: генератор {crossing[0]:.2f} дБм")
        ax.set_xlabel("Мощность, заданная на генераторе, дБм")
        ax.set_ylabel("Мощность на выходе усилителя, дБм")
        ax.set_title(f"Амплитудная характеристика, {f:g} МГц")
        ax.grid(True)
        ax.legend()
        fig.tight_layout()
        filename = f"04_p1db_characteristic_{f:g}MHz.png"
        fig.savefig(GRAPHS / filename, dpi=200)
        if not SHOW_PLOTS:
            plt.close(fig)
        print("  График:", filename)

    if processed_points:
        save_results(pd.concat(processed_points).sort_values(["f_MHz", "Pgen_dBm"]),
                     "result_04_p1db_points.csv")
    status = pd.DataFrame(
        status_rows,
        columns=["f_MHz", "n_points", "Pgen_max_dBm", "max_compression_dB",
                 "OP1dB_dBm", "status"]
    ).sort_values("f_MHz")
    save_results(status, "result_05_p1db_status.csv")
    if results_p1db:
        res = pd.DataFrame(results_p1db,
                           columns=["f_MHz", "Pgen_at_1dB_dBm", "IP1dB_dBm",
                                    "OP1dB_dBm", "Kp0_dB"])
        res = res.sort_values("f_MHz")
        save_results(res, "result_05_p1db.csv")
    fig, (ax_top, ax_bottom) = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    good = status.dropna(subset=["max_compression_dB"])
    ax_top.scatter(good["f_MHz"], good["max_compression_dB"], s=65)
    ax_top.axhline(1, color="tab:red", linestyle="--", label="Порог 1 дБ")
    for _, row in good.iterrows():
        ax_top.annotate(f"{row['max_compression_dB']:.2f} дБ\n"
                        f"до {row['Pgen_max_dBm']:g} дБм",
                        (row["f_MHz"], row["max_compression_dB"]),
                        xytext=(5, 7), textcoords="offset points", fontsize=8)
    ax_top.set_ylabel("Макс. измеренная компрессия, дБ")
    ax_top.set_title("Все измеренные частоты: достигнут ли порог 1 дБ?")
    ax_top.grid(True)
    ax_top.legend()
    if results_p1db:
        ax_bottom.scatter(res["f_MHz"], res["OP1dB_dBm"], s=65)
        for _, row in res.iterrows():
            ax_bottom.annotate(f"{row['OP1dB_dBm']:.2f} дБм",
                               (row["f_MHz"], row["OP1dB_dBm"]),
                               xytext=(5, 7), textcoords="offset points")
        ax_bottom.set_ylim(res["OP1dB_dBm"].min() - 1,
                           res["OP1dB_dBm"].max() + 1)
    ax_bottom.set_ylabel("OP1dB, дБм")
    ax_bottom.set_xlabel("Частота, МГц")
    ax_bottom.set_title("OP1dB только там, где пересечён порог")
    ax_bottom.set_xlim(p["f_MHz"].min() - 50, p["f_MHz"].max() + 50)
    ax_bottom.set_xticks(status["f_MHz"])
    ax_bottom.tick_params(axis="x", labelrotation=45)
    ax_bottom.grid(True)
    fig.tight_layout()
    fig.savefig(GRAPHS / "05_op1db_vs_frequency.png", dpi=200)
    if not SHOW_PLOTS:
        plt.close(fig)
    print("  График: 05_op1db_vs_frequency.png")
else:
    print("  Нет данных для P1dB или нет калибровки.")


# -----------------------------------------------------------
# 4. ИНТЕРМОДУЛЯЦИЯ ТРЕТЬЕГО ПОРЯДКА IP3 — 3.3.4
# -----------------------------------------------------------
print("\n4. IP3")
cal3 = load_csv("05_ip3_cal.csv").dropna(subset=["f_MHz", "P1_dBm", "P2_dBm"])
im = load_csv("06_ip3.csv").dropna(
    subset=["f_MHz", "P_tone_an_dBm", "P_IM3_an_dBm"])

if not cal3.empty and not im.empty:
    im = im.merge(cal3, on="f_MHz", how="inner")
    if not gain.empty:
        im = im.merge(gain, on="f_MHz", how="left")
    else:
        im["Kp_dB"] = np.nan

    im["IL3_dB"] = im["P2_dBm"] - im["P1_dBm"]
    im["P_tone_out_dBm"] = im["P_tone_an_dBm"] + im["IL3_dB"]
    im["P_IM3_out_dBm"] = im["P_IM3_an_dBm"] + im["IL3_dB"]
    im["IMD3_dB"] = im["P_tone_out_dBm"] - im["P_IM3_out_dBm"]
    im["OIP3_dBm"] = im["P_tone_out_dBm"] + im["IMD3_dB"] / 2
    im["IIP3_dBm"] = im["OIP3_dBm"] - im["Kp_dB"]

    for f, one in im.groupby("f_MHz"):
        one = one.dropna(subset=["P_in_tone_dBm"]).sort_values("P_in_tone_dBm")
        if len(one) < 2:
            print(f"  {f:g} МГц: для графика наклонов IP3 нужно >=2 входных уровней.")
            continue
        plt.figure(figsize=(8, 5))
        plt.plot(one["P_in_tone_dBm"], one["P_tone_out_dBm"], "o", label="Основной тон")
        plt.plot(one["P_in_tone_dBm"], one["P_IM3_out_dBm"], "s", label="Продукт IM3")
        # Прямые с наклонами 1:1 и 3:1 (экстраполяция по определению IP3).
        # Для каждой: Pout = slope * Pin + offset.
        b1 = (one["P_tone_out_dBm"] - one["P_in_tone_dBm"]).mean()
        b3 = (one["P_IM3_out_dBm"] - 3 * one["P_in_tone_dBm"]).mean()
        x_ip3 = (b1 - b3) / 2
        x_right = max(one["P_in_tone_dBm"].max(), x_ip3)
        xs = np.linspace(one["P_in_tone_dBm"].min(), x_right, 100)
        plt.plot(xs, xs + b1, "--", label="Экстраполяция 1:1")
        plt.plot(xs, 3 * xs + b3, "--", label="Экстраполяция 3:1")
        if x_ip3 >= one["P_in_tone_dBm"].min():
            plt.plot(x_ip3, x_ip3 + b1, "x", markersize=9, label="IP3 (экстрап.)")
        plt.xlabel("Входная мощность одного тона, дБм")
        plt.ylabel("Выходная мощность, дБм")
        plt.title(f"Интермодуляционные характеристики, {f:g} МГц")
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        filename = f"06_ip3_characteristic_{f:g}MHz.png"
        plt.savefig(GRAPHS / filename, dpi=200)
        if not SHOW_PLOTS:
            plt.close()
        print("  График:", filename)

    save_results(im.sort_values("f_MHz"), "result_06_ip3_points.csv")
    summary = im.groupby("f_MHz", as_index=False)[["OIP3_dBm", "IIP3_dBm"]].mean()
    graph(summary["f_MHz"], summary["OIP3_dBm"], "Частота, МГц", "OIP3, дБм",
          "Выходная IP3 от частоты", "07_oip3_vs_frequency.png")
    if summary["IIP3_dBm"].notna().any():
        valid = summary.dropna(subset=["IIP3_dBm"])
        graph(valid["f_MHz"], valid["IIP3_dBm"], "Частота, МГц", "IIP3, дБм",
              "Входная IP3 от частоты", "08_iip3_vs_frequency.png")
    save_results(summary, "result_07_ip3.csv")
else:
    print("  Нет данных для IP3 или нет калибровки.")

print("\nГотово. Графики (PNG):", GRAPHS)
print("Расчётные таблицы: файлы result_*.csv рядом со скриптом.")


# -----------------------------------------------------------
# 5. ОТРАЖЕНИЕ ПО ВХОДУ/ВЫХОДУ (ДОПОЛНИТЕЛЬНО)
# В методичке входит в цели, но подробного пункта в 3.3 нет.
# -----------------------------------------------------------
print("\n5. Коэффициенты отражения (дополнительно)")
r = load_csv("07_reflection_optional.csv")
for port in ["in", "out"]:
    fields = ["f_MHz", f"P_open_{port}_dBm", f"P_ref_{port}_dBm"]
    subset = r.dropna(subset=fields).copy()
    if subset.empty:
        continue
    tag = "S11" if port == "in" else "S22"
    subset[f"{tag}_dB"] = subset[f"P_ref_{port}_dBm"] - subset[f"P_open_{port}_dBm"]
    subset = subset.sort_values("f_MHz")
    graph(subset["f_MHz"], subset[f"{tag}_dB"], "Частота, МГц",
          f"{tag}, дБ", f"Модуль коэффициента отражения {tag}",
          f"09_{tag.lower()}.png" if port == "in" else f"10_{tag.lower()}.png")
    save_results(subset[["f_MHz", f"{tag}_dB"]], f"result_{tag.lower()}.csv")

print("\nВСЕ ИЗМЕРЕНИЯ ОБРАБОТАНЫ.")
if SHOW_PLOTS and plt.get_fignums():
    print("Открываю интерактивные графики. Закройте их окна для завершения программы.")
    plt.show(block=True)
