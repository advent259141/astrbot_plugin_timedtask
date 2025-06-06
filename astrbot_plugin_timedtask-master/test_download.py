import requests
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = 'https://multimedia.nt.qq.com.cn/download?appid=1407&fileid=EhRD61_ff8T0ZQD9IAEbmhLM9ZqPBxjL8Qcg_woowZGvvZPcjQMyBHByb2RQgL2jAVoQOwBFPpqlu01iGJ_7FNeCuXoCa5Y&rkey=CAQSMAo_zh89-YNO_oHw8mVBYl3U2dwmOFqdbeehPaFlAzri8sm0j1fmMQy9j8zD3aqi0g'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Connection': 'keep-alive'
}

print('测试URL访问...')
print(f'URL: {url[:100]}...')

try:
    print('\n方法1：禁用SSL验证...')
    response = requests.get(url, headers=headers, timeout=15, verify=False)
    print(f'状态码: {response.status_code}')
    print(f'响应大小: {len(response.content)} bytes')
    print(f'Content-Type: {response.headers.get("Content-Type", "未知")}')
    
    if response.status_code == 200:
        print('✅ 成功！可以下载图片')
        # 尝试保存图片
        with open('test_image.jpg', 'wb') as f:
            f.write(response.content)
        print('图片已保存为 test_image.jpg')
    else:
        print('❌ 失败')
        
except Exception as e:
    print(f'❌ 方法1失败: {e}')

try:
    print('\n方法2：使用session...')
    session = requests.Session()
    session.verify = False
    session.headers.update(headers)
    response = session.get(url, timeout=15)
    print(f'状态码: {response.status_code}')
    print(f'响应大小: {len(response.content)} bytes')
    
    if response.status_code == 200:
        print('✅ Session方式成功！')
    
except Exception as e:
    print(f'❌ 方法2失败: {e}')
