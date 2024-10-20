from fastapi import APIRouter, HTTPException, Depends
from binance.exceptions import BinanceAPIException
from api.models import TradingSignal
from api.binance_operations import BinanceOperations
from api.dependencies import create_binance_client
from api.logger import logger
import os
from decimal import Decimal


router = APIRouter()
OrderType = 1
def get_binance_ops(is_test: bool = True):
    return BinanceOperations(create_binance_client)

# 添加一个新函数来获取杠杆值
def get_leverage():
    return int(os.getenv('LEVERAGE', '1'))  # 默认值为3

# 更新 create_trade 函数的签名
@router.post("/trade")
async def create_trade(signal: TradingSignal, binance_ops: BinanceOperations = Depends(get_binance_ops)):
    if OrderType == 1:
        order_type = 'MARKET'
    else:
        order_type = 'LIMIT'
    try:
        logger.info(f"收到交易信号: {signal}")
        
        # 获取当前持仓信息
        current_position = binance_ops.get_positions(signal.symbol)
        logger.info(f"当前持仓: {current_position}")
        # 获取环境变量中的杠杆倍数
        env_leverage = get_leverage()
        # 解析新策略仓位
        new_position_size = Decimal(str(signal.position_size))
        
        if current_position:
            current_position_amount = Decimal(current_position['positionAmt'])
            current_leverage = int(current_position['leverage'])
            
            if current_position_amount != 0:
                current_side = '多头' if current_position_amount > 0 else '空头'
                logger.info(f"当前持仓方向: {current_side}, 数量: {abs(current_position_amount)}, 杠杆: {current_leverage}")
                
                # 平仓逻辑
                if new_position_size == 0 or (current_position_amount > 0 and new_position_size < 0) or (current_position_amount < 0 and new_position_size > 0):
                    logger.info(f"平仓: {signal.symbol} {current_side} {abs(current_position_amount)}")
                    close_order = binance_ops.close_position(signal.symbol, 'BOTH', float(current_position_amount))
                    logger.info(f"平仓订单结果: {simplify_order(close_order)}")
                    
                    # 平仓后调整杠杆倍数
                    if current_leverage != env_leverage:
                        binance_ops.set_leverage(signal.symbol, env_leverage)
                        logger.info(f"已将杠杆倍数从 {current_leverage} 调整为 {env_leverage}")
                    
                    if new_position_size == 0:
                        return {"消息": f"交易执行成功 - 平仓", "订单": simplify_order(close_order)}
            else:
                logger.info("当前无持仓")
                # 如果当前无持仓但杠杆不一致，调整杠杆倍数
                if current_leverage != env_leverage:
                    binance_ops.set_leverage(signal.symbol, env_leverage)
                    logger.info(f"已将杠杆倍数从 {current_leverage} 调整为 {env_leverage}")
        else:
            logger.info("当前无持仓")
            # 如果没有持仓信息，设置初始杠杆
            binance_ops.set_leverage(signal.symbol, env_leverage)
            logger.info(f"已设置初始杠杆倍数为 {env_leverage}")
        
        # 如果新策略仓位不为0，且与当前持仓方向不同或当前无持仓，则开新仓
        if new_position_size != 0 and (not current_position or current_position_amount == 0 or (current_position_amount > 0 and new_position_size < 0) or (current_position_amount < 0 and new_position_size > 0)):
            usdt_balance = binance_ops.get_usdt_balance()
            logger.info(f"USDT 余额: {usdt_balance}")
            
            current_price = binance_ops.get_current_price(signal.symbol)
            logger.info(f"{signal.symbol} 当前价格: {current_price}")
            
            # 计算交易数量，使用全部可用余额
            quantity = binance_ops.calculate_quantity(signal.symbol, usdt_balance, current_price)
            
            direction = 'BUY' if new_position_size > 0 else 'SELL'
            logger.info(f"开仓: {signal.symbol} {direction} {quantity}, 杠杆: {env_leverage}")
            order = binance_ops.create_order(signal.symbol, direction, quantity, env_leverage, order_type)
            simplified_order = simplify_order(order)
            logger.info(f"订单结果: {simplified_order}")
            
            return {"消息": f"交易执行成功", "订单": simplified_order}
        else:
            usdt_balance = binance_ops.get_usdt_balance()
            logger.info(f"当前持仓方向与新策略仓位方向一致，无需操作。当前USDT余额: {usdt_balance}")
            return {"消息": f"当前持仓方向与新策略仓位方向一致，无需操作。当前USDT余额: {usdt_balance}"}
        
    except BinanceAPIException as e:
        logger.error(f"币安 API 异常: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"意外错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
def simplify_order(order):
    return {
        'symbol': order['symbol'],
        'side': order['side'],
        'quantity': order['executedQty'],
        'price': order['avgPrice'] if 'avgPrice' in order else order['price'],
        'leverage': order.get('leverage', 'N/A')  # 使用 get 方法，如果 'leverage' 不存在，返回 'N/A'
    }
