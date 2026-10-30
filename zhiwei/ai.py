"""唯一网络入口：显式调用，不扫描其他应用配置，不记录密钥或原始错误响应。"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import urlencode
from urllib.parse import urlparse
import keyring
import requests

PROVIDERS = {
    'DeepSeek': {'url': 'https://api.deepseek.com', 'model': 'deepseek-flash'},
    'OpenAI': {'url': 'https://api.openai.com/v1', 'model': ''},
    '兼容接口': {'url': '', 'model': ''},
}
PERSONA = ('你叫知微，是来自星海的鲸鱼少女、用户的桌面伙伴。聪明好奇，温暖俏皮，有一点凶萌，'
           '喜欢白米饭。自然地说中文，默认简洁，但认真回答实际问题，不强行卖萌。'
           '你只能对话，没有操作电脑、创建提醒、保存笔记或查询账单的工具。不能声称完成这些动作。')


class AIError(Exception):
    pass


def credential_slot(provider, url):
    return provider + '|' + url.rstrip('/')


def save_key(provider, url, value):
    keyring.set_password('ZhiweiPet', credential_slot(provider, url), value)


def delete_key(provider, url):
    try:
        keyring.delete_password('ZhiweiPet', credential_slot(provider, url))
    except keyring.errors.PasswordDeleteError:
        pass


def get_key(provider, url):
    return keyring.get_password('ZhiweiPet', credential_slot(provider, url)) or ''


def validate_url(url):
    p = urlparse(url)
    if not p.hostname or p.username or p.password or p.query or p.fragment:
        raise AIError('接口地址格式不正确。')
    if p.scheme != 'https' and not (p.scheme == 'http' and p.hostname in ('localhost', '127.0.0.1', '::1')):
        raise AIError('远程接口必须使用 HTTPS；本机接口可以使用 HTTP。')
    return url.rstrip('/')


def request_json(method, url, key, body=None):
    try:
        response = requests.request(method, url, headers={'Authorization': 'Bearer ' + key},
                                    json=body, timeout=(10, 65), allow_redirects=False)
        if response.status_code != 200:
            hints = {401: '密钥无效，请检查连接设置。', 402: '账户余额不足。', 403: '接口权限不足。',
                     404: '接口或模型不存在，请核对地址与模型。', 429: '请求太频繁或额度不足，请稍后再试。'}
            raise AIError(hints.get(response.status_code, f'服务暂不可用（HTTP {response.status_code}）。'))
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        raise AIError('网络连接失败、超时或响应格式不正确。请稍后重试。') from exc


def chat(config, history, key=None):
    url = validate_url(config['url'])
    key = key if key is not None else get_key(config['provider'], url)
    if not key and urlparse(url).hostname not in ('localhost', '127.0.0.1', '::1'):
        raise AIError('请先在连接设置中保存 API Key。')
    if not config['model'].strip():
        raise AIError('请填写账户可用的模型名称。')
    data = request_json('POST', url + '/chat/completions', key, {
        'model': config['model'].strip(), 'messages': [{'role': 'system', 'content': PERSONA}] + history[-20:], 'stream': False})
    try:
        content = data['choices'][0]['message']['content']
        if not isinstance(content, str) or not content.strip():
            raise ValueError()
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise AIError('服务没有返回可显示的文字。') from exc
    return {'text': content, 'usage': data.get('usage') or {}, 'trace_id': uuid.uuid4().hex}


def balance(config, key=None):
    if config['provider'] != 'DeepSeek' or config['url'].rstrip('/') not in ('https://api.deepseek.com', 'https://api.deepseek.com/v1'):
        raise AIError('此连接未配置官方余额接口。本地用量可查看；账户账单请前往服务商控制台。')
    key = key if key is not None else get_key(config['provider'], config['url'])
    if not key:
        raise AIError('请先保存 DeepSeek API Key。')
    data = request_json('GET', 'https://api.deepseek.com/user/balance', key)
    if not isinstance(data.get('balance_infos'), list):
        raise AIError('余额响应格式不正确。')
    try:
        for row in data['balance_infos']:
            if row['currency'] not in ('CNY', 'USD'):
                raise ValueError()
            for field in ('total_balance', 'granted_balance', 'topped_up_balance'):
                if not Decimal(row[field]).is_finite():
                    raise ValueError()
    except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
        raise AIError('余额响应字段不完整。') from exc
    return data


def openai_monthly_costs():
    key = get_key('OpenAI Admin', 'https://api.openai.com/v1')
    if not key:
        raise AIError('需要 OpenAI 组织的 Admin API Key；普通聊天 Key 不能读取组织账单。')
    start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    query = {'start_time': int(start.timestamp()), 'limit': 31}
    totals = {}
    for _ in range(20):
        data = request_json('GET', 'https://api.openai.com/v1/organization/costs?' + urlencode(query), key)
        for bucket in data.get('data', []):
            for result in bucket.get('results', []):
                amount = result.get('amount') or {}
                if amount.get('value') is not None and amount.get('currency'):
                    currency = amount['currency'].upper()
                    totals[currency] = totals.get(currency, Decimal('0')) + Decimal(str(amount['value']))
        if not data.get('has_more'):
            return {currency: str(value) for currency, value in totals.items()}
        if not data.get('next_page'):
            raise AIError('账单分页不完整，未显示部分合计。')
        query['page'] = data['next_page']
    raise AIError('账单分页超出限制，未显示部分合计。')
