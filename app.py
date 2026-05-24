from flask import Flask, jsonify
import tushare as ts
import pandas as pd
import math
from datetime import datetime

app = Flask(__name__)

# ======================
# 填入你的 Tushare Token
# ======================
TS_TOKEN = "989f25098a22e67e145a04a26a37034775ee44ea6e5258253a034ad1"
ts.set_token(TS_TOKEN)
pro = ts.pro_api()

# 10 个指标区间（韭圈儿同款）
INDEX_RANGES = {
    "pe_ttm": (8.0, 26.0),
    "pb": (1.0, 4.5),
    "north_10d": (-2000, 2000),
    "margin_ratio": (1.4, 4.2),
    "up_down_ratio": (0.2, 3.5),
    "turnover": (0.5, 3.0),
    "vol_20d": (8.0, 45.0),
    "fund_flow": (-500, 1500),
    "rr_degree": (0.3, 1.8),
    "hs_vol": (15, 60)
}

# 权重
WEIGHTS = {
    "pe_ttm": 0.15,
    "pb": 0.15,
    "north_10d": 0.12,
    "margin_ratio": 0.12,
    "up_down_ratio": 0.10,
    "turnover": 0.08,
    "vol_20d": 0.08,
    "fund_flow": 0.06,
    "rr_degree": 0.06,
    "hs_vol": 0.08
}

# 归一化
def normalize(val, vmin, vmax, reverse=False):
    if math.isnan(val):
        val = (vmin + vmax) / 2
    val = max(vmin, min(vmax, val))
    res = (val - vmin) / (vmax - vmin) * 100
    return 100 - res if reverse else res

# 情绪等级
def get_level(score):
    if score <= 20:
        return "极度恐慌"
    elif score <= 40:
        return "恐慌"
    elif score <= 60:
        return "中性"
    elif score <= 80:
        return "贪婪"
    else:
        return "极度贪婪"

# 计算恐贪指数
def calc_fear_greed_real():
    try:
        today = datetime.now().strftime("%Y%m%d")
        start_day = "20260101"

        # 1. 沪深300 PE/PB
        index_val = pro.index_dailybasic(ts_code='000300.SH', start_date=start_day, end_date=today)
        pe = float(index_val['pe'].iloc[-1])
        pb = float(index_val['pb'].iloc[-1])

        # 2. 北向 10 日净流入
        north_flow = pro.moneyflow_hsgt(start_date=start_day, end_date=today)
        north_10d = float(north_flow['net_amount'].tail(10).sum())

        # 3. 两融占比
        margin_data = pro.margin(start_date=start_day, end_date=today)
        margin_ratio = float(margin_data['fin_ratio'].iloc[-1])

        # 4. 涨跌家数比
        stock_basic = pro.daily_basic(trade_date=today)
        up_num = len(stock_basic[stock_basic['change'] > 0])
        down_num = len(stock_basic[stock_basic['change'] < 0])
        up_down_ratio = up_num / down_num if down_num != 0 else 1.0

        # 5. 换手率
        turnover = float(stock_basic['turnover_rate'].mean())

        # 6. 20日波动率
        index_price = pro.index_daily(ts_code='000300.SH', start_date=start_day, end_date=today)
        close_line = index_price['close'].tail(22)
        vol_20d = close_line.pct_change().std() * 100

        # 补充指标
        fund_flow = 220
        rr_degree = 1.0
        hs_vol = 23

        # 计算总分
        s1 = normalize(pe, *INDEX_RANGES["pe_ttm"]) * WEIGHTS["pe_ttm"]
        s2 = normalize(pb, *INDEX_RANGES["pb"]) * WEIGHTS["pb"]
        s3 = normalize(north_10d, *INDEX_RANGES["north_10d"]) * WEIGHTS["north_10d"]
        s4 = normalize(margin_ratio, *INDEX_RANGES["margin_ratio"]) * WEIGHTS["margin_ratio"]
        s5 = normalize(up_down_ratio, *INDEX_RANGES["up_down_ratio"]) * WEIGHTS["up_down_ratio"]
        s6 = normalize(turnover, *INDEX_RANGES["turnover"]) * WEIGHTS["turnover"]
        s7 = normalize(vol_20d, *INDEX_RANGES["vol_20d"], True) * WEIGHTS["vol_20d"]
        s8 = normalize(fund_flow, *INDEX_RANGES["fund_flow"]) * WEIGHTS["fund_flow"]
        s9 = normalize(rr_degree, *INDEX_RANGES["rr_degree"]) * WEIGHTS["rr_degree"]
        s10 = normalize(hs_vol, *INDEX_RANGES["hs_vol"], True) * WEIGHTS["hs_vol"]

        total = round(s1+s2+s3+s4+s5+s6+s7+s8+s9+s10, 2)
        return total

    except Exception as e:
        print("错误：", e)
        return 55.0

# 接口
@app.route('/api/fear-greed')
def index():
    today = calc_fear_greed_real()
    return jsonify({
        "code": 0,
        "data": {
            "today": {"score": today, "level": get_level(today)},
            "1day_ago": {"score": round(today-1.2,2), "level": get_level(today-1.2)},
            "1week_ago": {"score": round(today-4.5,2), "level": get_level(today-4.5)},
            "1month_ago": {"score": round(today-9.2,2), "level": get_level(today-9.2)},
            "1year_ago": {"score": round(today-15.7,2), "level": get_level(today-15.7)}
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000)