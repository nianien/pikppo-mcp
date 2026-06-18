from pydantic import BaseModel


class StockQuote(BaseModel):
    symbol: str  # 标的代码（解析后）
    name: str
    market: str  # 市场标签：沪A/深A/港股/美股 等
    price: float  # 最新价
    change: float  # 涨跌额
    change_pct: float  # 涨跌幅 %
    open: float
    high: float
    low: float
    prev_close: float
    amplitude_pct: float | None = None  # 振幅 %
    turnover_pct: float | None = None  # 换手率 %
    volume: float  # 成交量（A股/港股：手；美股：股）
    amount: float  # 成交额（本币）
    volume_ratio: float | None = None  # 量比
    pe: float | None = None  # 市盈率（动态），部分市场无则为 null
    pb: float | None = None  # 市净率
    market_cap: float | None = None  # 总市值（本币）
    float_market_cap: float | None = None  # 流通市值（本币）
    updated_at: str  # 数据时间（北京时间 ISO8601）；行情通常有延迟


class KlinePoint(BaseModel):
    date: str  # YYYY-MM-DD（分钟级时为 YYYY-MM-DD HH:mm）
    open: float
    close: float
    high: float
    low: float
    volume: float
    amount: float
    change_pct: float  # 当根涨跌幅 %


class StockHistory(BaseModel):
    symbol: str
    name: str
    market: str
    period: str  # daily/weekly/monthly/1min...
    adjust: str  # qfq/hfq/none
    points: list[KlinePoint]  # 按日期升序
    start_close: float  # 区间首根收盘
    end_close: float  # 区间末根收盘
    high: float  # 区间最高价
    low: float  # 区间最低价
    change_pct: float  # 区间涨跌幅 = (end_close-start_close)/start_close*100
    max_drawdown_pct: float  # 最大回撤 %（基于收盘价，负值或 0）
    ma: dict[str, float | None]  # 末根收盘的均线：ma5/ma10/ma20，数据不足为 null


class FinancialIndicator(BaseModel):
    report: str  # 报告期名称，如 2026一季报
    report_type: str  # 报告类型：一季报/中报/三季报/年报
    notice_date: str  # 披露日期 YYYY-MM-DD
    revenue: float | None = None  # 营业总收入（本币元）
    revenue_yoy: float | None = None  # 营收同比 %
    net_profit: float | None = None  # 归母净利润（元）
    net_profit_yoy: float | None = None  # 归母净利同比 %
    net_profit_excl: float | None = None  # 扣非归母净利润（元）
    eps: float | None = None  # 每股收益（元）
    bps: float | None = None  # 每股净资产（元）
    roe: float | None = None  # 净资产收益率(加权) %
    net_margin: float | None = None  # 销售净利率 %
    gross_margin: float | None = None  # 销售毛利率 %
    debt_ratio: float | None = None  # 资产负债率 %


class StockFundamentals(BaseModel):
    symbol: str
    name: str
    market: str
    currency: str  # 报表币种
    periods: list[FinancialIndicator]  # 按报告期降序，最新在前


class Announcement(BaseModel):
    date: str  # 公告日期 YYYY-MM-DD
    type: str  # 公告分类，如「财务报告」「高管人员任职变动」
    title: str


class StockAnnouncements(BaseModel):
    symbol: str
    name: str
    market: str
    announcements: list[Announcement]  # 按日期降序，最新在前


class DividendRecord(BaseModel):
    report: str  # 对应报告期 YYYY-MM-DD
    notice_date: str  # 预案/实施公告日 YYYY-MM-DD
    plan: str | None = None  # 分红方案描述
    progress: str | None = None  # 进度：预披露/预案/实施 等
    pretax_cash_per10: float | None = None  # 每 10 股税前现金分红（元）
    ex_dividend_date: str | None = None  # 除权除息日 YYYY-MM-DD


class StockDividends(BaseModel):
    symbol: str
    name: str
    market: str
    dividends: list[DividendRecord]  # 按报告期降序，最新在前
