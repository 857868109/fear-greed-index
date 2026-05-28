# -*- coding: utf-8 -*-
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import os
import sys
import warnings
warnings.filterwarnings('ignore')

def calculate_fear_greed():
    """获取上证指数并计算简化版恐贪指数"""
    print("=" * 50)
    print("A股恐贪指数日报生成器")
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # 默认报告内容（防止完全失败）
    default_report = f"""# 📊 A股恐贪指数日报 - {datetime.now().strftime('%Y-%m-%d')}

## ⚠️ 数据获取失败

今日无法获取实时行情数据，可能原因：
- 非交易时段
- 网络连接问题
- 数据源暂时不可用

请稍后再试。

📌 **免责声明**：本报告仅供参考，不构成投资建议。
"""
    
    try:
        # 1. 获取数据
        print("\n[1/4] 获取指数数据...")
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=240)).strftime('%Y%m%d')
        
        # 尝试获取上证指数数据
        df = None
        try:
            df = ak.stock_zh_a_hist(symbol="000001", period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
        except Exception as e:
            print(f"  方式1失败: {e}")
            # 备用方式
            try:
                df = ak.index_zh_a_hist(symbol="000001", period="daily", start_date=start_date, end_date=end_date)
            except Exception as e2:
                print(f"  方式2也失败: {e2}")
        
        if df is None or df.empty:
            print("❌ 无法获取指数数据，生成默认报告")
            with open('fear_greed_report.md', 'w', encoding='utf-8') as f:
                f.write(default_report)
            return True
            
        # 重命名列
        df.rename(columns={'日期': 'date', '收盘': 'close', '最高': 'high', '最低': 'low'}, inplace=True)
        df = df.sort_values('date')
        print(f"✓ 获取到 {len(df)} 条数据")
        
        # 2. 计算恐贪指数 (20日周期)
        print("[2/4] 计算恐贪指数...")
        period = 20
        if len(df) < period:
            print(f"❌ 数据不足（{len(df)} < {period}），无法计算")
            with open('fear_greed_report.md', 'w', encoding='utf-8') as f:
                f.write(default_report)
            return True
            
        df['high_max'] = df['high'].rolling(window=period).max()
        df['low_min'] = df['low'].rolling(window=period).min()
        df['fear_greed'] = (df['close'] - df['low_min']) / (df['high_max'] - df['low_min']) * 100
        df['fear_greed'] = df['fear_greed'].fillna(50).clip(0, 100)
        
        # 3. 获取最新数据
        latest = df.iloc[-1]
        fg_value = latest['fear_greed']
        
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
        
        print(f"✓ 恐贪指数: {fg_value:.1f}")
        print(f"✓ 情绪状态: {sentiment}")
        
        # 获取涨跌家数（可选，失败不影响主报告）
        print("[3/4] 获取市场统计数据...")
        up = 0
        down = 0
        try:
            spot_df = ak.stock_zh_a_spot()
            if '涨跌幅' in spot_df.columns:
                up = spot_df[spot_df['涨跌幅'] > 0].shape[0]
                down = spot_df[spot_df['涨跌幅'] < 0].shape[0]
                print(f"✓ 上涨: {up}, 下跌: {down}")
            else:
                print("⚠ 涨跌幅列不存在，跳过")
        except Exception as e:
            print(f"⚠ 获取涨跌数据失败: {e}")
        
        # 4. 生成Markdown报告
        print("[4/4] 生成日报...")
        today_str = datetime.now().strftime('%Y-%m-%d')
        
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
| 涨跌比 | {up/down if down > 0 else up:.2f} |

## 📉 近期恐贪指数走势（近10日）

| 日期 | 恐贪值 | 情绪 |
|:---|:---|:---|
"""
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

### 操作参考

- **极度恐惧时（≤25）**：市场超跌，可逢低吸纳优质资产
- **恐惧时（25-44）**：市场情绪偏谨慎，建议控制仓位
- **中性时（45-55）**：情绪平稳，可关注结构性机会
- **贪婪时（56-75）**：市场情绪偏热，注意回调风险
- **极度贪婪时（≥75）**：市场过热，建议逐步减仓

---

📌 **免责声明**：本报告基于公开数据自动生成，仅供参考，不构成任何投资建议。市场有风险，投资需谨慎。
"""
        # 保存报告
        with open('fear_greed_report.md', 'w', encoding='utf-8') as f:
            f.write(report)
            
        print("\n" + "=" * 50)
        print("✅ 报告生成成功！")
        print(f"📄 文件路径: {os.path.abspath('fear_greed_report.md')}")
        print(f"📊 报告大小: {os.path.getsize('fear_greed_report.md')} 字节")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"\n❌ 运行出错: {e}")
        import traceback
        traceback.print_exc()
        # 生成错误报告
        with open('fear_greed_report.md', 'w', encoding='utf-8') as f:
            f.write(default_report + f"\n\n**错误详情**: {str(e)}")
        return True  # 返回True以便继续发布默认报告

if __name__ == "__main__":
    calculate_fear_greed()
