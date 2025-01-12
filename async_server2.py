import asyncio
import socket
import json
import uuid
import PostgresDatabase
import PaypalClient
import aiofiles
import requests
import urllib.parse
import secrets

class AsyncioServer:
    ppc = PaypalClient.PaypalClient()
    access_token = ppc.get_access_token()
    def __init__(self, host='localhost', port=8000):
        self.host = host
        self.port = port
        self.client_data = {}  # Dictionary to store client address and their message

    async def update_html(self, writer, html_file, dict_obj):
        async with aiofiles.open(html_file, 'r') as f:
            file_contents = await f.read()
        single_checked = "checked" if dict_obj['single'] else ""
        file_contents = file_contents.format(
            height=dict_obj['height'],
            weight=dict_obj['weight'],
            single_checked=single_checked
        )
        return file_contents

    async def update_api_html(self, writer, html_file, dict_obj):
        async with aiofiles.open(html_file, 'r') as f:
            file_contents = await f.read()
        print(file_contents)
        file_contents = file_contents.format(
            client_name=dict_obj['app_name']
        )
        print(file_contents)
        return file_contents
    
    async def update_user_subscription(self,writer,cookie,dict_obj):
        self.db = PostgresDatabase.PostgresDatabase()
        self.db.connect()
        query = "UPDATE public.users SET subscription = %s WHERE session_id = %s"
        self.db.execute_non_query(query,(dict_obj['tier'],cookie,))
        self.db.close()
        return
            
    async def update_user_info(self,writer,cookie,dict_obj):
        self.db = PostgresDatabase.PostgresDatabase()
        self.db.connect()
        query = "UPDATE public.users SET height = %s, weight = %s, single = %s WHERE session_id = %s"
        self.db.execute_non_query(query,(dict_obj['height'],dict_obj['weight'],dict_obj['single'],cookie,))
        self.db.close()
        return

    async def retrieve_user_info(self,writer,cookie):
        self.db = PostgresDatabase.PostgresDatabase()
        self.db.connect()
        query = "SELECT * FROM public.users WHERE session_id = '{}'".format(cookie)
        user_info = list(self.db.execute_query(query))
        self.db.close()
        column_names = user_info[::-1].pop(0)
        result = []
        for row in user_info[0]:
            row_dict = dict(zip(column_names, row))
            result.append(row_dict)
        return result

    async def authenticate_user(self,writer,username,password):
        self.db = PostgresDatabase.PostgresDatabase()
        self.db.connect()
        query = "SELECT * FROM public.users WHERE username = %s and password=%s"
        user_info = self.db.execute_query(query, (username,password,))
        if user_info:
            self.db.close()
            return True
        if not user_info:
            self.db.close()
            return False

    async def add_new_user(self,writer,email,username,password):
        self.db = PostgresDatabase.PostgresDatabase()
        self.db.connect()
        query ="INSERT INTO public.users (username, password, email)VALUES (%s, %s, %s);"
        new_user = self.db.execute_non_query(query, (username, password,email))
        print(new_user)
        if new_user == 'Username Exists':
            await self.send_302(writer,'/register')
        if new_user != 'Username Exists':
            await self.send_302(writer,'/login')
        self.db.close()
        return

    async def register_app(self,writer,app_name,app_uri):
        client_id = str(uuid.uuid4())
        client_secret = secrets.token_urlsafe(32) 
        self.db = PostgresDatabase.PostgresDatabase()
        self.db.connect()
        query ="INSERT INTO public.oauth_clients(client_id, client_secret, name, redirect_uri)VALUES (%s, %s, %s, %s);"
        new_app = self.db.execute_non_query(query, (client_id, client_secret, app_name, app_uri,))
        if new_app == 'Username Exists':
            await self.send_302(writer,'/dashboard')
        if new_app != 'Username Exists':
            await self.send_302(writer,'/api-authorize')
        self.db.close()
        print('here')
        return

    async def send_302(self, writer, target_url):
        response = "HTTP/1.1 302 Found\r\nLocation: {}\r\nContent-Length: 0\r\nConnection: close\r\n\r\n".format(target_url)
        await self.send_to_client(writer, response)
        return

    async def update_user_cookie(self,writer,cookie,username):
        self.db = PostgresDatabase.PostgresDatabase()
        self.db.connect()
        query = "UPDATE public.users SET session_id = %s WHERE username = %s"
        self.db.execute_non_query(query, (cookie, username))
        self.db.close()
        return

    async def send_cookie(self, writer, cookie, username):
        response = "HTTP/1.1 302 Found\r\nLocation: /dashboard\r\nSet-Cookie: {}\r\nContent-Length: 0\r\nConnection: close\r\n\r\n".format(cookie)
        await self.update_user_cookie(writer,cookie,username)
        await self.send_to_client(writer, response)
        return
        
    async def send_to_client(self, writer, response):
        encoded_response = response.encode('utf-8')
        print(encoded_response)
        writer.write(encoded_response)
        await writer.drain()
        writer.close()
        return

    async def send_200(self, writer, file_path, raw_html):
        if raw_html == None:
            ok_response = "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=UTF-8\r\nConnection: close\r\n\r\n"
            with open(file_path,'r')  as f:
                file_content = f.read()            
            response = ok_response + file_content
            encoded_response = response.encode('utf-8')
            await self.send_to_client(writer, response)
            return
        if file_path == None:
            ok_response = "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=UTF-8\r\nConnection: close\r\n\r\n"       
            response = ok_response + raw_html
            encoded_response = response.encode('utf-8')
            await self.send_to_client(writer, response)
            return
        
    async def handle_get(self, writer, request_dict):
        if request_dict['GET'] == '/':
            await self.send_200(writer, r'C:/server/index.html', None)
        if request_dict['GET'] == '/login':
            await self.send_200(writer, r'C:/server/login.html', None)
        if request_dict['GET'] == '/register':
            await self.send_200(writer, r'C:/server/register.html', None)
        if request_dict['GET'] == '/about':
            await self.send_200(writer, r'C:/server/about.html', None)
        if request_dict['GET'] == '/contact':
            await self.send_200(writer, r'C:/server/contact.html', None)
        if request_dict['GET'] == '/dashboard' and 'Cookie' in request_dict:
            await self.send_200(writer, r'C:/server/logged-in/dashboard.html', None)
        if request_dict['GET'] == '/dashboard' and 'Cookie' not in request_dict:
            await self.send_200(writer, r'C:/server/login.html', None)
        if request_dict['GET'] == '/user-profile' and 'Cookie' in request_dict:
            user_info = await self.retrieve_user_info(writer , request_dict['Cookie'])
            user_page = await self.update_html(writer, 'C:/server/logged-in/user-profile.html', user_info[0])
            await self.send_200(writer, None, user_page)
            pass
        if request_dict['GET'] == '/data-analytics' and 'Cookie' in request_dict:
            await self.send_200(writer, r"C:\server\logged-in\data-analytics.html", None)
            pass
        if request_dict['GET'] == '/notifications' and 'Cookie' in request_dict:
            await self.send_200(writer, r"C:\server\logged-in\notifications.html", None)
            pass
        if request_dict['GET'] == '/admin-controls' and 'Cookie' in request_dict:
            await self.send_200(writer, r"C:\server\logged-in\admin-controls.html", None)
            pass
        if request_dict['GET'] == '/api-documentation' and 'Cookie' in request_dict:
            await self.send_200(writer, r"C:\server\logged-in\api-documentation.html", None)
            pass
        if request_dict['GET'] == '/settings' and 'Cookie' in request_dict:
            await self.send_200(writer, r"C:\server\logged-in\settings.html", None)
            pass
        if request_dict['GET'] == '/reports' and 'Cookie' in request_dict:
            await self.send_200(writer, r"C:\server\logged-in\reports.html", None)
            pass
        if request_dict['GET'] == '/support' and 'Cookie' in request_dict:
            await self.send_200(writer, r"C:\server\logged-in\support.html", None)
            pass
        if request_dict['GET'] == '/settings/manage-subscription' and 'Cookie' in request_dict:
            await self.send_200(writer, r"C:\server\logged-in\settings\manage-subscription.html", None)
            pass
        if request_dict['GET'] == '/register-app' and 'Cookie' in request_dict:
            await self.send_200(writer, r"C:\server\logged-in\register-app.html", None)
        return

    async def handle_post(self, writer, request_dict):
        if request_dict['POST'] == '/register-app':
            app_dict = {}
            application_info = [key for key, value in request_dict.items() if value == 'non_header'][0].split('&')
            app_name = application_info[0].split('=')[1]
            app_uri = urllib.parse.unquote(application_info[1].split('=')[1])
            app_dict['app_name'] = app_name
            app_dict['app_uri'] = app_uri
            print(app_name,app_uri)
            app_auth = await self.update_api_html(writer, "C:/server/logged-in/api-authorize.html", app_dict)
            await self.register_app(writer,app_name,app_uri)
            print(app_auth)
            await self.send_200(writer,None,app_auth)
            return
        
        if request_dict['POST'] == '/authenticate':
            credential_dict = [key for key, value in request_dict.items() if value == 'non_header'][0].split('&')
            username= credential_dict[0].split('=')[1]
            password = credential_dict[1].split('=')[1]
            user_exists = await self.authenticate_user(writer,username,password)
            if user_exists:
                cookie_uuid = str(uuid.uuid4())
                await self.send_cookie(writer, cookie_uuid, username)
            if not user_exists:
                await self.send_302(writer,'/register')

        if request_dict['POST'] == '/add-new-user':
            print(request_dict)
            credential_dict = [key for key, value in request_dict.items() if value == 'non_header'][0].split('&')
            email = credential_dict[0].split('=')[1]
            username = credential_dict[1].split('=')[1]
            password = credential_dict[2].split('=')[1]
            user_exists = await self.add_new_user(writer,email,username,password)
            print('here')
            
                
        if request_dict['POST'] == '/update-user-profile':
            dict_obj = {}
            user_profile_dict = [key for key, value in request_dict.items() if value == 'non_header'][0].split('&')
            dict_obj['height'] = user_profile_dict[0].split('=')[1]
            dict_obj['weight'] = user_profile_dict[1].split('=')[1]
            if 'single=on' in str(user_profile_dict):
                dict_obj['single'] = 'true'
            if 'single=on' not in str(user_profile_dict):
                dict_obj['single'] = 'false'
            await self.update_user_info(writer,request_dict['Cookie'],dict_obj)
            await self.send_302(writer,'/user-profile')

        if request_dict['POST'] == '/settings/manage-subscription/submit':
            for thing in request_dict:
                if 'subscription=' in thing:
                    username = await self.retrieve_user_info(writer, request_dict['Cookie'])
                    username = username[0]['username']
                    subscription_tier = {}
                    subscription_tier['tier'] = thing.split('=')[1]
            if subscription_tier['tier'] == 'basic':
                return_url = AsyncioServer.ppc.create_payment(username, '5.00', 'USD', 'Updating Subscription: Basic', 'http://localhost:8000/dashboard', 'https://example.com')
            if subscription_tier['tier'] == 'standard':
                return_url = AsyncioServer.ppc.create_payment(username, '10.00', 'USD', 'Updating Subscription: Standard', 'http://localhost:8000/dashboard', 'https://example.com')
            if subscription_tier['tier'] == 'premium':
                return_url = AsyncioServer.ppc.create_payment(username, '20.00', 'USD', 'Updating Subscription: Premium', 'http://localhost:8000/dashboard', 'https://example.com')
            redirect_url = return_url['links'][1]['href']
            await self.send_302(writer, redirect_url)
            await self.update_user_subscription(writer, request_dict['Cookie'], subscription_tier)
        return

    async def handle_options(self, writer, request_dict):
        response = "HTTP/1.1 200 OK\r\nAccess-Control-Allow-Origin: http://127.0.0.1:8000\r\nAccess-Control-Allow-Methods: POST, GET, OPTIONS\r\nAccess-Control-Allow-Headers: Content-Type\r\nAccess-Control-Allow-Credentials: true\r\nContent-Length: 0\r\n\r\n"
        await self.send_to_client(writer, response)
        return

    async def complete_transaction(self, writer, request_dict):
        http = request_dict['GET'].split('&')
        payment_id = http[0].split('=')[1]
        token = http[1].split('=')[1]
        payer_id = http[2].split('=')[1].split('\n')[0].split(' ')[0]
        request = 'https://api.sandbox.paypal.com/v1/payments/payment/{}/execute'.format(payment_id)
        headers = {"Content-Type": "application/json","Authorization": "Bearer {}".format(AsyncioServer.access_token),}
        data = {"payer_id": payer_id}
        r = requests.post(request,json=data, headers=headers)
        await self.send_302(writer, '/')
        self.db.close()
        
    async def handle_request(self, writer, request_dict):
        if 'GET' in request_dict:
            if 'paymentId=PAYID-' and 'token=' and 'PayerID=' in request_dict['GET']:
                await self.complete_transaction(writer , request_dict)
            await self.handle_get(writer, request_dict)
        if 'POST' in request_dict:
            await self.handle_post(writer, request_dict)
        if 'OPTIONS' in request_dict:
            await self.handle_options(writer, request_dict)
        return

    async def parse_message(self, message):
        http_as_list = message.split('\r\n')
        print(http_as_list)
        request = http_as_list.pop(0).split(' ')
        request_type = request[0]
        request_target =request[1]
        headers_dict = {}
        for header in http_as_list:
            try:                
                if header != '':
                    header = header.split(': ')
                    headers_dict[header[0]] = header[1]
            except:
                headers_dict[header[0]] = 'non_header'
        headers_dict[request_type] = request_target
        headers_json = headers_dict
        return headers_json

    async def handle_client(self, reader, writer):
        data = await reader.read(1024)
        message = data.decode('utf-8')
        addr = writer.get_extra_info('peername')
        self.client_data[addr] = await self.parse_message(message)
        await self.handle_request(writer, self.client_data[addr])
        return

    async def start_server(self):
        server = await asyncio.start_server(
            self.handle_client, self.host, self.port
        )
        addr = server.sockets[0].getsockname()
        async with server:
            await server.serve_forever()
        return

if __name__ == "__main__":
    server = AsyncioServer(host='localhost', port=8000)
    asyncio.run(server.start_server())
