"""Лабораторная работа № 2: АЧХ, отражение и аттенюаторы.

Запуск: python lab2_plot.py
Исходные измерения: CSV-файлы в папке input.
Результаты: CSV в results и рисунки PNG в graphs.

Только экспериментальные данные. Пропуски не заполняются выдуманными числами.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parent
INPUT = BASE / "input"
RESULTS = BASE / "results"
GRAPHS = BASE / "graphs"
RESULTS.mkdir(exist_ok=True)
GRAPHS.mkdir(exist_ok=True)

# Используем шрифт, поддерживающий кириллицу.
plt.rcParams["font.family"] = "Times New Roman"
plt.rcParams["axes.grid"] = True


def read_measurements(filename, columns):
    """Чтение CSV с ; и проверка столбцов, чисел, частот."""
    path = INPUT / filename
    if not path.exists():
        raise FileNotFoundError(f"Нет файла {path}. Проверь папку input.")

    data = pd.read_csv(path, sep=";", dtype=str, encoding="utf-8-sig")
    data.columns = data.columns.str.strip()
    missing = [name for name in columns if name not in data.columns]
    if missing:
        raise ValueError(f"{filename}: отсутствуют столбцы {missing}.")
    data = data[columns].copy()

    for col in columns:
        raw = data[col].fillna("").astype(str).str.strip()
        raw = raw.str.replace("\u00a0", "", regex=False).str.replace(" ", "", regex=False)
        raw = raw.str.replace(",", ".", regex=False)
        # Пустые клетки становятся NaN; ошибочные записи обнаруживаем.
        number = pd.to_numeric(raw.replace("", np.nan), errors="coerce")
        wrong = raw.ne("") & (number.isna() | ~np.isfinite(number))
        if wrong.any():
            rows = [str(i + 2) for i in data.index[wrong][:8]]
            raise ValueError(f"{filename}, столбец {col}: некорректное число в строках {', '.join(rows)}.")
        data[col] = number

    # Удаляем строки без частоты, только если остальные клетки пусты.
    no_frequency = data["f_MHz"].isna()
    if data.loc[no_frequency, columns[1:]].notna().any().any():
        raise ValueError(f"{filename}: есть измерение без частоты f_MHz.")
    data = data.loc[~no_frequency].copy()

    if (data["f_MHz"] <= 0).any():
        raise ValueError(f"{filename}: частоты должны быть больше 0 МГц.")
    if data["f_MHz"].duplicated().any():
        dup = data.loc[data["f_MHz"].duplicated(keep=False), "f_MHz"].tolist()
        raise ValueError(f"{filename}: повторяющиеся частоты {dup} МГц.")

    return data.sort_values("f_MHz").reset_index(drop=True)


def save_table(data, filename):
    data.to_csv(RESULTS / filename, sep=";", decimal=",", index=False,
                encoding="utf-8-sig", float_format="%.5f")


def graph(filename, title, ylabel, data, series):
    """series: список (название столбца, подпись кривой)."""
    fig, ax = plt.subplots(figsize=(9, 5))
    x_max = data["f_MHz"].max()
    drawn = False

    for col, label in series:
        if data[col].notna().any():
            # Сохраняем пропуски NaN, чтобы линия в этих местах прерывалась.
            ax.plot(data["f_MHz"], data[col], "o-", ms=4, lw=1.5, label=label)
            drawn = True
    if drawn:
        ax.set_title(title)
        ax.set_xlabel("Частота, МГц")
        ax.set_ylabel(ylabel)

        if filename == "01_ACHX.png":

            x_min, x_max = ax.get_xlim()


        ax.legend()
        fig.tight_layout()
        fig.savefig(GRAPHS / filename, dpi=300)
        print("  График:", filename)
    else:
        print("  Пропущен график (нет данных):", filename)
    plt.close(fig)

def achx():
    print("\n[1] АЧХ фильтра")
    df = read_measurements("achx.csv", ["f_MHz", "P_filter_dBm", "P_cal_dBm"])
    df["S21_dB"] = df["P_filter_dBm"] - df["P_cal_dBm"]
    save_table(df, "01_achx_results.csv")
    graph("01_ACHX.png", "АЧХ фильтра ",
          "S₂₁, дБ", df, [("S21_dB", "S₂₁")])
    print("  Полных частотных точек:", int(df["S21_dB"].notna().sum()))
    return df


def reflection():
    print("\n[2] Коэффициент отражения фильтра")
    df = read_measurements("reflection.csv",
                           ["f_MHz", "P_OC_dBm", "P_50_dBm", "P_filter_dBm"])
    # В методичке: в дБ величину отражения оценивают относительно ХХ.
    df["Gamma_dB"] = df["P_filter_dBm"] - df["P_OC_dBm"]
    df["Gamma_abs"] = 10 ** (df["Gamma_dB"] / 20)
    df["ReturnLoss_dB"] = -df["Gamma_dB"]  # положительные возвратные потери
    # Разность уровней OC и 50 Ом — ОЦЕНКА предельной развязки / направленности.
    df["D_est_dB"] = df["P_OC_dBm"] - df["P_50_dBm"]

    # |Г| > 1 невозможно для пассивной нагрузки. При |Г| = 1 КСВН
    # бесконечен. Ни то ни другое не заменяем искусственным 0.95.
    valid = df["Gamma_abs"].ge(0) & df["Gamma_abs"].lt(1)
    df["VSWR"] = np.nan
    df.loc[valid, "VSWR"] = ((1 + df.loc[valid, "Gamma_abs"]) /
                               (1 - df.loc[valid, "Gamma_abs"]))

    # Рядом с фоном от согласованной нагрузки малые отражения нельзя
    # надёжно определять простым вычитанием уровней мощностей.
    near_floor = (df["P_filter_dBm"].notna() & df["P_50_dBm"].notna() &
                  (df["P_filter_dBm"] <= df["P_50_dBm"] + 6))
    df["Quality"] = ""
    df.loc[near_floor, "Quality"] = "Близко к фону 50 Ом (<=6 дБ)"
    df.loc[df["Gamma_abs"].eq(1), "Quality"] = "|Г|=1: КСВН бесконечен"
    df.loc[df["Gamma_abs"].gt(1), "Quality"] = "|Г|>1: недостоверное измерение"

    save_table(df, "02_reflection_results.csv")
    graph("02_Reflected_power.png", "Отражённый сигнал: разные нагрузки",
          "Уровень в измерительном плече, дБм", df,
          [("P_OC_dBm", "ХХ (разомкнутый выход)"),
           ("P_50_dBm", "Нагрузка 50 Ом"),
           ("P_filter_dBm", "Фильтр + 50 Ом")])
    graph("03_VSWR.png", "КСВН фильтра", "КСВН", df,
          [("VSWR", "КСВН = (1+|Г|)/(1−|Г|)")])

    # Отражение (отрицательные дБ) и направленность (положительные дБ)
    # показаны на разных вертикальных осях: единицы и смысл отличаются.
    if df["Gamma_dB"].notna().any() or df["D_est_dB"].notna().any():
        fig, ax1 = plt.subplots(figsize=(9, 5))
        ax2 = ax1.twinx()
        lines = []
        if df["Gamma_dB"].notna().any():
            lines += ax1.plot(df["f_MHz"], df["Gamma_dB"], "o-", ms=4,
                              label="20lg|Г|, дБ")
        if df["D_est_dB"].notna().any():
            lines += ax2.plot(df["f_MHz"], df["D_est_dB"], "s--", ms=4,
                              label="Оценка направленности D, дБ")
        ax1.set_xlabel("Частота, МГц")
        ax1.set_ylabel("Коэффициент отражения 20lg|Г|, дБ")
        ax2.set_ylabel("Оценка направленности D, дБ")
        ax1.set_title("Отражение фильтра и оценка направленности ответвителя")
        ax1.legend(lines, [line.get_label() for line in lines], loc="best")
        fig.tight_layout()
        fig.savefig(GRAPHS / "04_Gamma_and_D.png", dpi=300)
        plt.close(fig)
        print("  График: 04_Gamma_and_D.png")
    else:
        print("  Пропущен график: 04_Gamma_and_D.png")

    print("  Полных точек отражения:", int(df["Gamma_dB"].notna().sum()))
    print("  Недостоверных точек (у фона 50 Ом):", int(near_floor.sum()))
    print("  Точек с бесконечным КСВН (|Г|=1):", int(df["Gamma_abs"].eq(1).sum()))
    print("  Недостоверных точек (|Г|>1):", int(df["Gamma_abs"].gt(1).sum()))
    return df


def attenuators(refl):
    print("\n[3] Ненагруженные аттенюаторы")
    att = read_measurements("attenuators.csv",
                            ["f_MHz", "P_att3_dBm", "P_att6_dBm", "P_att10_dBm"])
    # Опорные ХХ и 50 Ом берём из reflection.csv только на совпадающих
    # частотах. Не сопоставляем строки по порядковому номеру!
    ref = refl[["f_MHz", "P_OC_dBm", "P_50_dBm"]]
    df = att.merge(ref, on="f_MHz", how="left", validate="one_to_one")
    for a in [3, 6, 10]:
        df[f"Gamma_att{a}_dB"] = df[f"P_att{a}_dBm"] - df["P_OC_dBm"]
    save_table(df, "03_attenuators_results.csv")
    graph("05_Attenuators_power.png", "Отражённый сигнал: аттенюаторы и нагрузки",
          "Уровень в измерительном плече, дБм", df,
          [("P_OC_dBm", "ХХ"), ("P_50_dBm", "50 Ом"),
           ("P_att3_dBm", "Ненагруженный 3 дБ"),
           ("P_att6_dBm", "Ненагруженный 6 дБ"),
           ("P_att10_dBm", "Ненагруженный 10 дБ")])

    fig, ax = plt.subplots(figsize=(9, 5))
    drawn = False
    for a in [3, 6, 10]:
        col = f"Gamma_att{a}_dB"
        if df[col].notna().any():
            ax.plot(df["f_MHz"], df[col], "o-", ms=4,
                    label=f"Измерено: {a} дБ")
            ax.axhline(-2*a, ls="--", lw=1,
                       label=f"Теория: −{2*a} дБ")
            drawn = True
    if drawn:
        ax.set_title("Отражение от ненагруженных аттенюаторов")
        ax.set_xlabel("Частота, МГц")
        ax.set_ylabel("20lg|Гвх|, дБ")
        ax.legend(ncol=2)
        fig.tight_layout()
        fig.savefig(GRAPHS / "06_Attenuators_Gamma.png", dpi=300)
        print("  График: 06_Attenuators_Gamma.png")
    else:
        print("  Пропущен график: 06_Attenuators_Gamma.png")
    plt.close(fig)

    no_ref = df["P_OC_dBm"].isna() & df[
        ["P_att3_dBm", "P_att6_dBm", "P_att10_dBm"]].notna().any(axis=1)
    if no_ref.any():
        missing_freq = df.loc[no_ref, "f_MHz"].tolist()
        print("  ВНИМАНИЕ: нет измерения ХХ на частотах", missing_freq,
              "МГц. Для них коэффициент отражения аттенюаторов не вычислен.")
    print("  Точек с мощностью хотя бы одного аттенюатора:",
          int(att[["P_att3_dBm", "P_att6_dBm", "P_att10_dBm"]].notna().any(axis=1).sum()))


def main():
    print("ЛР №2. Обработка экспериментальных данных (без подмены измерений)")
    achx()
    refl = reflection()
    attenuators(refl)
    print("\nГотово. Расчёты: results/; рисунки: graphs/.")
    print("Если CSV пока пустые, заполните их и повторно запустите программу.")


if __name__ == "__main__":
    main()
