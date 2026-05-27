# -*- coding: utf-8 -*-
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

def calculate_fear_greed():
    """获取上证指数并计算简化版恐贪指数"""
    try:
        # 1. 获取数据 (使用免费AKShare库)
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=240)).strftime('%Y%m%d')
        
        # 获取上证指数历史数据
        df = ak.stock_zh_a_hist(symbol="000001", period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
        
        if df is None or df.empty:
            print("获取数据失败")
            return None
            
        # 重命名列，方便处理
        df.rename(columns={'日期': 'date', '收盘': 'close', '最高': 'high', '最低': 'low'}, inplace=True)
        df = df.sort_values('date')
        
        # 2. 计算恐贪指数 (20日周期)
        period = 20
        df['high_max'] = df['high'].rolling(window=period).max()
        df['low_min'] = df['low'].rolling(window=period).min()
        
        # 恐贪指数 = (当前价 - 近期最低价) / (近期最高价 - 近期最低价) * 100
        df['fear_greed'] = (df['close'] - df['low_min']) / (df['high_max'] - df['low_min']) * 100
        df['fear_greed'] = df['fear_greed'].fillna(50).clip(0, 100)
        
        # 3. 获取最新数据和市场概况
        latest = df.iloc[-1]
        fg_value = latest['fear_greed']
        
        # 判断情绪
        if fg_value <= 25:
            sentiment = "极度恐惧 😨"
        elif fg_value <= 44:
            sentiment = "恐惧 😰"
        elif fg_value <= 55:
            sentiment = "中性 😑"
        elif fg_value <= 75:
            sentiment = "贪婪 😋"
        else:
            sentiment = "极度贪婪 🤩"
        
        # 获取涨跌家数
        spot_df = ak.stock_zh_a_spot()
        up = spot_df[spot_df['涨跌幅'] > 0].shape[0] if '涨跌幅' in spot_df.columns else 0
        down = spot_df[spot_df['涨跌幅'] < 0].shape[0] if '涨跌幅' in spot_df.columns else 0
        
        # 4. 生成Markdown报告
        today_str = datetime.now().strftime('%Y-%m-%d %A')
        report = f"""# 📊 A股恐贪指数日报 - {today_str}

## 📈 今日市场情绪
| 指数 | 恐贪值 | 情绪状态 | 最新收盘 |
|:---|:---|:---|:---|
| 上证指数 | **{fg_value:.1f}** | **{sentiment}** | {latest['close']:.2f} |

## 📊 市场统计数据
| 指标 | 数值 |
|:---|:---|
| 上涨家数 | {up} |
| 下跌家数 | {down} |
| 涨跌比 | {up/down if down>0 else up:.2f} |

## 📉 近期恐贪指数走势 (近10日)
| 日期 | 恐贪值 | 情绪 |
|:---|:---|:---|
"""
        # 添加最近10天的数据
        for _, row in df.tail(10).iterrows():
            date_str = row['date'].strftime('%m-%d')
            val = row['fear_greed']
            if val <= 25:
                sta = "极度恐惧"
            elif val <= 44:
                sta = "恐惧"
            elif val <= 55:
                sta = "中性"
            elif val <= 75:
                sta = "贪婪"
            else:
                sta = "极度贪婪"
            report += f"| {date_str} | {val:.1f} | {sta} |\n"
            
        report += f"""
## 💡 投资小贴士
> 当前恐贪指数为 **{fg_value:.1f}**，市场处于 **{sentiment}** 状态。
> * **{fg_value:.1f} ≤ 25 (极度恐惧)**：市场可能被过度悲观情绪笼罩，或可留意中长期布局机会。
> * **{fg_value:.1f} ≥ 75 (极度贪婪)**：市场情绪可能过于亢奋，短期需留意回调风险。
>
> 📌 **免责声明**：本报告仅为数据展示和自动化测试，不构成任何投资建议。市场有风险，投资需谨慎。
"""
        # 保存报告
        with open('fear_greed_report.md', 'w', encoding='utf-8') as f:
            f.write(report)
            
        print("✅ 报告生成成功！")
        return True
        
    except Exception as e:
        print(f"❌ 运行出错: {e}")
        return False

if __name__ == "__main__":
    calculate_fear_greed()
