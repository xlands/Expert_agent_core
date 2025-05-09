import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import router
import uvicorn


def create_app():
    """创建并配置FastAPI应用"""
    app = FastAPI(title="Cotex AI Search API")
    
    # 启用CORS，允许所有来源访问
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由
    app.include_router(router, prefix="")
    
    # 配置超时设置（作为应用状态存储）
    app.state.USER_QUERY_TIMEOUT = 60  # 用户查询超时时间(秒)
    app.state.SERVER_QUERY_TIMEOUT = 600  # 服务器查询超时时间(秒)
    app.state.DATA_PROCESSING_TIMEOUT = 30  # 数据原子化处理超时时间(秒)
    app.state.INTERRUPT_TIMEOUT = 5  # 中断请求处理超时时间(秒)
    
    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8001))
    uvicorn.run("app.app:app", host="0.0.0.0", port=port, reload=True)