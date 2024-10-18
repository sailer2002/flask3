from functools import lru_cache
from binance.client import Client
import os

# 从环境变量获取Binance API密钥
LIVE_API_KEY = 'GROsv2OaXeYoyn9IHTCQd1BdAsIiOg6oHWxRwONq6c3nt4tPZnH2Vr5fXwnmyRvs'
LIVE_API_SECRET = 'Bem7lsfhx82zMw0FNnUM4fY2HeTv4bd55RCuc8L6ttqNYRgYxCEAussiZPcwwEmC'

# 模拟交易的API密钥
TEST_API_KEY = "36e0defa187a7540841ae47d5715f474d0f2ec1b9f11b98f9efa1e1d7287cf9c"
TEST_API_SECRET = "785608aab998e138be470333f3ad97392c4a771bd4cdbf3dc6d2717a38e38e00"

@lru_cache()
def create_binance_client() -> Client:
    return Client(LIVE_API_KEY, LIVE_API_SECRET, testnet=False)
    #return Client(LIVE_API_KEY, LIVE_API_SECRET)


