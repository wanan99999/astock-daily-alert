# -*- coding: utf-8 -*-
"""风格比值（只作参考，不参与预警信号）

比值1 = 创业板指 ÷ 中证红利；比值2 = 创业板50 ÷ 红利低波100（都用价格指数收盘价）。
写 data/ratio.json；任何数据源失败都保留旧文件，不影响主站。
"""
import os
import json
import datetime
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
OUT = os.path.join(DATA, "ratio.json")

# 参考线：低于 lo = 创业板相对红利偏便宜；高于 hi = 偏贵（2023 起回测：单独当买卖开关不如原方案，只作提示）
RATIOS = [
    dict(id="r1", name="比值1：创业板指 ÷ 中证红利", a=("sina", "sz399006", "创业板指"), b=("cs", "000922", "中证红利"), lo=0.35, hi=0.65, since="2010-06-01"),
    dict(id="r2", name="比值2：创业板50 ÷ 红利低波100", a=("sina", "sz399673", "创业板50"), b=("cs", "930955", "红利低波100"), lo=0.15, hi=0.30, since="2014-06-18"),
]


def _series(src, code):
    import akshare as ak
    if src == "sina":
        d = ak.stock_zh_index_daily(symbol=code)
        s = d.set_index(pd.to_datetime(d["date"]))["close"]
    else:
        d = ak.stock_zh_index_hist_csindex(symbol=code, start_date="20050101",
                                           end_date=datetime.date.today().strftime("%Y%m%d"))
        s = d.set_index(pd.to_datetime(d["日期"]))["收盘"]
    return s.astype(float).sort_index()


def update():
    try:
        old = json.load(open(OUT, encoding="utf-8"))
    except Exception:
        old = {}
    out = {"updated": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d %H:%M"), "items": []}
    for R in RATIOS:
        try:
            a, b = _series(*R["a"][:2]), _series(*R["b"][:2])
            df = pd.DataFrame({"a": a, "b": b}).dropna()
            df = df[df.index >= R["since"]]
            r = (df["a"] / df["b"])
            now = float(r.iloc[-1])
            wk = r.resample("W-FRI").last().dropna()
            if wk.index[-1] < r.index[-1]:
                wk.loc[r.index[-1]] = now
            r3 = r[r.index >= r.index[-1] - pd.Timedelta(days=365 * 3)]
            out["items"].append(dict(
                id=R["id"], name=R["name"], a=R["a"][2], b=R["b"][2], lo=R["lo"], hi=R["hi"],
                date=r.index[-1].strftime("%Y-%m-%d"), now=round(now, 4),
                a_close=round(float(df["a"].iloc[-1]), 2), b_close=round(float(df["b"].iloc[-1]), 2),
                chg20=round(float(now / r.iloc[-21] - 1), 4) if len(r) > 21 else None,
                pct_all=round(float((r < now).mean()), 4), pct_3y=round(float((r3 < now).mean()), 4),
                min=round(float(r.min()), 4), max=round(float(r.max()), 4), since=r.index[0].strftime("%Y-%m-%d"),
                curve=dict(d=[x.strftime("%Y-%m-%d") for x in wk.index], v=[round(float(v), 4) for v in wk.values])))
            print("%s：%.3f（%s）" % (R["name"], now, r.index[-1].date()))
        except Exception as e:  # noqa: BLE001
            print("风格比值 %s 取数失败，沿用旧数据：%s %s" % (R["id"], type(e).__name__, e))
            prev = [x for x in old.get("items", []) if x.get("id") == R["id"]]
            if prev:
                out["items"].append(prev[0])
    if out["items"]:
        json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    return out


if __name__ == "__main__":
    update()
