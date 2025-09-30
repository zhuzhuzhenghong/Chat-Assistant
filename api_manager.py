import requests
import json
from typing import Dict, List, Optional, Any

class APIManager:
    """简化的API管理类 - 以用户数据为中心的粗粒度操作"""
    
    def __init__(self, base_url: str = "http://localhost:8000/api"):
        self.base_url = base_url
        self.session = requests.Session()
        self.user_id = None  # 为登录功能预留
        
        # 设置默认headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def set_user_auth(self, user_id: str, token: Optional[str] = None):
        """设置用户认证信息（为登录功能预留）"""
        self.user_id = user_id
        if token:
            self.session.headers.update({'Authorization': f'Bearer {token}'})
    
    def _make_request(self, method: str, url: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """统一的请求处理方法"""
        url = f"{self.base_url}/{url.lstrip('/')}"
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=data)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, json=data)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"API请求失败: {str(e)}")
    
    # ==================== 核心数据操作（粗粒度） ====================
    
    def get_user_data(self, user_id: str = None) -> Dict[str, Any]:
        """获取用户完整数据
        
        返回格式:
        {
            "user_id": "user123",
            "scripts_data": {
                "公司话术": {
                    "常用": {
                        "问候语": ["您好，很高兴为您服务！", ...],
                        "结束语": ["感谢您的咨询！", ...]
                    },
                    "产品介绍": {...}
                },
                "小组话术": {...},
                "私人话术": {...}
            },
            "config_data":{

            }
            "last_updated": "2024-01-01T12:00:00Z"
        }
        """
        uid = user_id or self.user_id or "default"
        result = self._make_request('GET', f'/user/{uid}/data')
        return result
    
    def save_user_data(self, data: Dict[str, Any], user_id: str = None) -> Dict[str, Any]:
        """保存用户完整数据
        
        参数:
        data: 完整的用户数据结构
        """
        uid = user_id or self.user_id or "default"
        request_data = {
            'user_id': uid,
            'data': data
        }
        result = self._make_request('PUT', f'/user/{uid}/data', request_data)
        return result

    
    # ==================== 用户管理（为登录功能预留） ====================
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """用户登录"""
        request_data = {
            'username': username,
            'password': password
        }
        result = self._make_request('POST', '/auth/login', request_data)
        
        if result.get('success'):
            user_id_result = result.get('user_id')
            token_result = result.get('token')
            if user_id_result:
                self.set_user_auth(user_id_result, token_result)
        
        return result
    
    def logout(self) -> Dict[str, Any]:
        """用户登出"""
        result = self._make_request('POST', '/auth/logout')
        if result.get('success'):
            self.user_id = None
            if 'Authorization' in self.session.headers:
                del self.session.headers['Authorization']
        return result
    
    # ==================== 文件导入导出（格式转换） ====================
    
    def upload_and_convert_file(self, file_path: str, user_id: str = None) -> Optional[Dict[str, Any]]:
        """上传文件并转换为JSON格式
        
        支持的文件格式：
        - Excel (.xlsx, .xls)
        - CSV (.csv)
        - JSON (.json)
        
        返回转换后的JSON数据结构
        """
        uid = user_id or self.user_id or "default"
        
        try:
            # 使用multipart/form-data上传文件
            url = f"{self.base_url}/file/upload-convert"
            
            with open(file_path, 'rb') as f:
                files = {'file': f}
                data = {'user_id': uid}
                
                # 临时移除Content-Type header让requests自动设置multipart
                original_headers = dict(self.session.headers)
                if 'Content-Type' in self.session.headers:
                    del self.session.headers['Content-Type']
                
                response = self.session.post(url, files=files, data=data)
                
                # 恢复原始headers
                self.session.headers.update(original_headers)
                
                response.raise_for_status()
                result = response.json()
                
                if result.get('success'):
                    return result.get('data')
                else:
                    print(f"文件转换失败: {result.get('message', '未知错误')}")
                    return None
                    
        except requests.exceptions.RequestException as e:
            print(f"文件上传失败: {str(e)}")
            return None
        except Exception as e:
            print(f"文件处理失败: {str(e)}")
            return None
    
    def export_and_convert_data(self, data: Dict[str, Any], file_path: str, 
                               file_format: str = "json", user_id: str = None) -> bool:
        """导出数据并转换为指定格式
        
        支持的导出格式：
        - json: JSON文件
        - excel: Excel文件 (.xlsx)
        - csv: CSV文件
        
        参数:
        data: 要导出的数据
        file_path: 导出文件路径
        file_format: 导出格式 (json/excel/csv)
        """
        uid = user_id or self.user_id or "default"
        
        try:
            request_data = {
                'user_id': uid,
                'data': data,
                'format': file_format.lower()
            }
            
            response = self.session.post(f"{self.base_url}/file/export-convert", json=request_data)
            response.raise_for_status()
            
            # 如果返回的是文件内容，直接保存
            if response.headers.get('content-type', '').startswith('application/'):
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                return True
            else:
                # 如果返回的是JSON响应
                result = response.json()
                if result.get('success'):
                    # 如果有文件URL，下载文件
                    if 'file_url' in result:
                        download_response = self.session.get(result['file_url'])
                        download_response.raise_for_status()
                        with open(file_path, 'wb') as f:
                            f.write(download_response.content)
                        return True
                    else:
                        print(f"导出失败: {result.get('message', '未知错误')}")
                        return False
                else:
                    print(f"导出失败: {result.get('message', '未知错误')}")
                    return False
                    
        except requests.exceptions.RequestException as e:
            print(f"文件导出失败: {str(e)}")
            return False
        except Exception as e:
            print(f"文件处理失败: {str(e)}")
            return False
    