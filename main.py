from fastapi import FastAPI, Request, HTTPException, Depends
from api.routes import router as api_router
from api.binance_operations import BinanceOperations
from api.dependencies import create_binance_client
from api.models import TradingSignal
from api.logger import logger
import re, uvicorn
from decimal import Decimal

app = FastAPI()

app.include_router(api_router, prefix="/api")

def get_binance_ops(is_test: bool = False):
    return BinanceOperations(create_binance_client)

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post('/webhook')
async def webhook(request: Request, binance_ops: BinanceOperations = Depends(get_binance_ops)):
    try:
        payload = (await request.body()).decode('utf-8')
        logger.info(f"收到 Webhook 请求: {payload}")

        # 解析请求内容
        symbol_match = re.search(r'成交(\w+)。', payload)
        position_match = re.search(r'新策略仓位([-]?\d+(\.\d+)?)', payload)

        symbol = symbol_match.group(1)
        new_position_size = Decimal(position_match.group(1))

        comment_match = re.search(r'comment(\w+)', payload) 
        comment = comment_match.group(1) if comment_match else ''

        # 创建 TradingSignal 对象
        signal = TradingSignal(
            symbol=symbol,
            direction='BUY' if new_position_size > 0 else 'SELL',
            position_size=float(new_position_size),  # 使用绝对值
            comment=comment
        )

        # 调用 create_trade 函数
        from api.routes import create_trade
        result = await create_trade(signal, binance_ops)
        return result

    except ValueError as e:
        logger.error(f"解析 Webhook 请求时发生错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"处理 Webhook 请求时发生意外错误: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")

# 这个条件语句确保在本地运行时才执行uvicorn.run()
# Vercel会自动处理应用的运行，不需要这部分代码
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

# 为Vercel部署添加这一行
# Vercel需要一个名为"app"的变量作为入口点
app = app
