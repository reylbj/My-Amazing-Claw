from flask import Flask, render_template, request, jsonify, redirect, url_for
import asyncio
import json
import os
from datetime import datetime
from loguru import logger
from context_manager import ChatContextManager
from multi_account_manager import multi_account_manager

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'xianyu-multi-account-secret-key')

# 全局变量
context_manager = ChatContextManager()

@app.route('/')
def index():
    """账号列表首页"""
    try:
        accounts = context_manager.get_all_accounts()
        return render_template('index.html', accounts=accounts)
    except Exception as e:
        logger.error(f"获取账号列表失败: {e}")
        return render_template('index.html', accounts=[], error=str(e))

@app.route('/account/new', methods=['GET', 'POST'])
def create_account():
    """创建新账号"""
    if request.method == 'GET':
        return render_template('create_account.html')
    
    try:
        data = request.get_json() if request.is_json else request.form
        
        account_name = data.get('account_name', '').strip()
        cookies = data.get('cookies', '').strip()
        user_id = data.get('user_id', '').strip()
        seller_enabled = bool(data.get('seller_enabled', True))
        buyer_enabled = bool(data.get('buyer_enabled', True))
        
        if not account_name or not cookies or not user_id:
            return jsonify({'success': False, 'message': '账号名、Cookie和用户ID不能为空'})
        
        # 创建账号
        account_id = context_manager.create_account(
            account_name=account_name,
            cookies=cookies,
            user_id=user_id,
            seller_enabled=seller_enabled,
            buyer_enabled=buyer_enabled
        )
        
        if account_id:
            logger.info(f"创建账号成功: {account_name} (ID: {account_id})")
            
            # 添加到多账号管理器 (异步操作需要特殊处理)
            account_config = context_manager.get_account_by_id(account_id)
            if account_config:
                # 在Flask线程中，我们不能直接调用asyncio，需要通过其他方式处理
                # 这里先记录，让系统在下次刷新时自动添加新账号
                logger.info(f"新账号 {account_name} 已创建，将在下次系统刷新时自动加载")
            
            return jsonify({'success': True, 'message': '账号创建成功', 'account_id': account_id})
        else:
            return jsonify({'success': False, 'message': '账号创建失败，可能账号名已存在'})
            
    except Exception as e:
        logger.error(f"创建账号时出错: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/account/<int:account_id>/config', methods=['GET', 'POST'])
def account_config(account_id):
    """账号配置页面"""
    if request.method == 'GET':
        try:
            account = context_manager.get_account_by_id(account_id)
            if not account:
                return render_template('error.html', message='账号不存在')
            
            prompts = context_manager.get_account_prompts(account_id)
            
            # 获取默认提示词模板
            default_prompts = {}
            prompt_types = ['classify', 'price', 'tech', 'default', 'buyer']
            for prompt_type in prompt_types:
                try:
                    with open(f'prompts/{prompt_type}_prompt.txt', 'r', encoding='utf-8') as f:
                        default_prompts[prompt_type] = f.read()
                except FileNotFoundError:
                    default_prompts[prompt_type] = f"# {prompt_type} 提示词\n请在此处编写提示词..."
            
            # 如果没有自定义提示词，使用默认的
            for prompt_type in prompt_types:
                if prompt_type not in prompts:
                    prompts[prompt_type] = default_prompts.get(prompt_type, '')
            
            return render_template('account_config.html', account=account, prompts=prompts)
            
        except Exception as e:
            logger.error(f"获取账号配置失败: {e}")
            return render_template('error.html', message=str(e))
    
    elif request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            
            # 更新账号基本信息
            account_updates = {}
            for field in ['account_name', 'cookies', 'seller_enabled', 'buyer_enabled']:
                if field in data:
                    if field in ['seller_enabled', 'buyer_enabled']:
                        account_updates[field] = bool(data[field])
                    else:
                        account_updates[field] = data[field].strip() if isinstance(data[field], str) else data[field]
            
            if account_updates:
                success = context_manager.update_account(account_id, **account_updates)
                if not success:
                    return jsonify({'success': False, 'message': '更新账号信息失败'})
            
            # 更新提示词
            prompt_types = ['classify', 'price', 'tech', 'default', 'buyer']
            for prompt_type in prompt_types:
                prompt_key = f'{prompt_type}_prompt'
                if prompt_key in data:
                    prompt_content = data[prompt_key].strip()
                    if prompt_content:
                        context_manager.save_account_prompt(account_id, prompt_type, prompt_content)
            
            # 配置已保存，多账号管理器会在监控循环中自动检测配置变化
            logger.info(f"账号配置已更新，将在下次刷新时生效: ID {account_id}")
            
            logger.info(f"账号配置已更新: ID {account_id}")
            return jsonify({'success': True, 'message': '配置保存成功'})
            
        except Exception as e:
            logger.error(f"保存账号配置时出错: {e}")
            return jsonify({'success': False, 'message': str(e)})

@app.route('/account/<int:account_id>/start', methods=['POST'])
def start_account(account_id):
    """启动账号"""
    try:
        # 确保账号存在
        account = context_manager.get_account_by_id(account_id)
        if not account:
            return jsonify({'success': False, 'message': '账号不存在'})
        
        logger.info(f"收到启动账号请求: {account['account_name']} (ID: {account_id})")
        
        # 简化处理：直接标记启动，由主系统的事件循环处理实际操作
        try:
            # 检查账号是否已经在管理器中
            if account_id not in multi_account_manager.account_managers:
                logger.info(f"账号 {account['account_name']} 不在管理器中，现在添加...")
                # 先添加账号到管理器
                add_result = asyncio.run(multi_account_manager.add_account(account))
                if not add_result:
                    return jsonify({'success': False, 'message': '无法添加账号到管理器'})
            
            # 使用线程安全的方式设置启动标志
            result = asyncio.run(multi_account_manager.start_account(account_id))
            if not result:
                return jsonify({'success': False, 'message': '启动账号失败'})
            # 这里我们简化处理，直接返回成功，让监控循环处理实际启动
            logger.info(f"账号启动请求已处理: {account['account_name']} (ID: {account_id})")
            return jsonify({'success': True, 'message': f"账号 {account['account_name']} 启动请求已发送，正在处理中..."})
        
        except Exception as e:
            logger.error(f"启动账号过程中出错: {e}")
            return jsonify({'success': False, 'message': str(e)})
        
    except Exception as e:
        logger.error(f"启动账号时出错: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/account/<int:account_id>/stop', methods=['POST'])
def stop_account(account_id):
    """停止账号"""
    try:
        account = context_manager.get_account_by_id(account_id)
        if not account:
            return jsonify({'success': False, 'message': '账号不存在'})
        
        logger.info(f"收到停止账号请求: {account['account_name']} (ID: {account_id})")
        
        # 检查账号是否在管理器中
        if account_id not in multi_account_manager.account_managers:
            logger.warning(f"账号 {account['account_name']} 不在管理器中，无法停止")
            return jsonify({'success': False, 'message': '账号未启动，无需停止'})
        
        # 简化处理：直接标记停止，由主系统处理
        result = asyncio.run(multi_account_manager.stop_account(account_id))
        if not result:
            return jsonify({'success': False, 'message': '停止账号失败'})
        try:
            logger.info(f"账号停止请求已处理: {account['account_name']} (ID: {account_id})")
            return jsonify({'success': True, 'message': f"账号 {account['account_name']} 停止请求已发送，正在处理中..."})
        
        except Exception as e:
            logger.error(f"停止账号过程中出错: {e}")
            return jsonify({'success': False, 'message': str(e)})
        
    except Exception as e:
        logger.error(f"停止账号时出错: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/account/<int:account_id>/delete', methods=['POST'])
def delete_account(account_id):
    """删除账号"""
    try:
        account = context_manager.get_account_by_id(account_id)
        if not account:
            return jsonify({'success': False, 'message': '账号不存在'})
        
        account_name = account['account_name']
        
        # 账号删除请求已记录，多账号管理器会在监控循环中处理
        logger.info(f"收到删除账号请求: {account_name} (ID: {account_id})")
        
        # 从数据库中删除
        success = context_manager.delete_account(account_id)
        
        if success:
            logger.info(f"删除账号: {account_name} (ID: {account_id})")
            return jsonify({'success': True, 'message': '账号删除成功'})
        else:
            return jsonify({'success': False, 'message': '删除账号失败'})
            
    except Exception as e:
        logger.error(f"删除账号时出错: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/accounts/status')
def get_accounts_status():
    """获取所有账号状态API"""
    try:
        accounts = context_manager.get_all_accounts()
        
        # 检查后台多账号管理器是否可用
        try:
            runtime_statuses = multi_account_manager.get_all_account_status()
        except Exception as e:
            logger.warning(f"获取运行时状态失败: {e}")
            runtime_statuses = []
        
        # 合并数据库状态和运行时状态
        status_map = {status['account_id']: status for status in runtime_statuses}
        
        for account in accounts:
            runtime_status = status_map.get(account['id'], {})
            account.update(runtime_status)
        
        return jsonify({'success': True, 'data': accounts})
        
    except Exception as e:
        logger.error(f"获取账号状态时出错: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/system/start_all', methods=['POST'])
def start_all_accounts():
    """启动所有账号"""
    try:
        logger.info("收到启动所有账号请求")
        
        # 获取所有启用的账号
        accounts = context_manager.get_all_accounts()
        active_accounts = [acc for acc in accounts if acc['status'] == 'active']
        
        if not active_accounts:
            return jsonify({'success': False, 'message': '没有可启动的账号'})
        
        # 确保所有账号都在管理器中
        for account in active_accounts:
            account_id = account['id']
            if account_id not in multi_account_manager.account_managers:
                asyncio.run(multi_account_manager.add_account(account))
        
        # 启动所有账号
        result = asyncio.run(multi_account_manager.start_all_accounts())
        if result:
            return jsonify({'success': True, 'message': f'已启动 {len(active_accounts)} 个账号'})
        else:
            return jsonify({'success': False, 'message': '启动部分账号失败'})
        
    except Exception as e:
        logger.error(f"启动所有账号时出错: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/system/stop_all', methods=['POST'])
def stop_all_accounts():
    """停止所有账号"""
    try:
        logger.info("收到停止所有账号请求")
        
        # 停止所有账号
        result = asyncio.run(multi_account_manager.stop_all_accounts())
        if result:
            return jsonify({'success': True, 'message': '已停止所有运行中的账号'})
        else:
            return jsonify({'success': False, 'message': '停止账号过程中出现错误'})
        
    except Exception as e:
        logger.error(f"停止所有账号时出错: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/monitor')
def monitor():
    """监控页面"""
    try:
        accounts = context_manager.get_all_accounts()
        return render_template('monitor.html', accounts=accounts)
    except Exception as e:
        logger.error(f"获取监控信息失败: {e}")
        return render_template('monitor.html', accounts=[], error=str(e))

@app.route('/settings')
def settings():
    """设置页面"""
    try:
        # 获取当前环境变量配置
        current_settings = {
            'HEARTBEAT_INTERVAL': os.getenv('HEARTBEAT_INTERVAL', '15'),
            'TOKEN_REFRESH_INTERVAL': os.getenv('TOKEN_REFRESH_INTERVAL', '3600'),
            'MANUAL_MODE_TIMEOUT': os.getenv('MANUAL_MODE_TIMEOUT', '3600'),
            'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO'),
        }
        return render_template('settings.html', settings=current_settings)
    except Exception as e:
        logger.error(f"获取设置信息失败: {e}")
        return render_template('settings.html', settings={}, error=str(e))

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', message='页面不存在'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', message='服务器内部错误'), 500


def run_flask_app(host='0.0.0.0', port=5002, debug=False):
    """运行Flask应用"""
    logger.info(f"启动Web管理界面: http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_flask_app(debug=True)