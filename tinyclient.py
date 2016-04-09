#! /usr/bin/env python3

'''This is a minimal client implementation, intended as an example. It simulates
logging into the game on your phone, obtaining any logging bonuses along the
way, and allows you to view the start-up notices (event info, etc.) in a
browser.

The script reads GameEngineActivity.xml in the current directory for account
information. If the file does not exist, a new account may be registered. You
could probably also use an existing GameEngineActivity.xml file from the actual
game. No promises on inter-operability, however.'''

import xml.etree.ElementTree as ET
import xml.etree
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import webbrowser

from llsifclient import LLSIFClient


def main_cmdline():
    client = LLSIFClient()
    
    try:
        conf = ET.parse('GameEngineActivity.xml')
        loginkey = conf.find("./string[@name='[LOVELIVE_ID]user_id']").text
        passwd = conf.find("./string[@name='[LOVELIVE_PW]passwd']").text
        print('Account information loaded.')
        
    except FileNotFoundError:
        print('No existing account found. Should I register a new game account?')
        a = input('[Y/n]:')
        
        if not a or a.lower()[0] == 'y':
            print('Registering new account...')
            
            loginkey, passwd = client.gen_new_credentials()
            r = ET.Element('map')
            ET.SubElement(r, 'string', name='[LOVELIVE_ID]user_id')
            ET.SubElement(r, 'string', name='[LOVELIVE_PW]passwd')
            r[0].text = loginkey
            r[1].text = passwd
            conf = ET.ElementTree(r)
            conf.write('GameEngineActivity.xml')
            print('    Account login information written to file.')
            
            client.register_new_account(loginkey, passwd)
            print('    New account registered.')
        else:
            print('Not registering new account. The program will now exit.')
            return
    
    # Simply call client.startapp() to simulate logging in if you don't need 
    # any custom logic.
    
    print('Logging in...')
    client.start_session()
    client.login(loginkey, passwd)
    
    userinfo = client.userinfo()
    # Printing Unicode characters in Windows console is such a mess
    try:
        print('    Nickname: {}'.format(userinfo['response_data']['user']['name']))
    except UnicodeEncodeError:
        print('    Nickname: {}'.format(ascii(userinfo['response_data']['user']['name'])))
    
    print("    Profile ID: {u[invite_code]}\n"
          "    Level: {u[level]:d}\n"
          "    Loveca: {u[sns_coin]:d}, "
          "G: {u[game_coin]:d}, Friend pts: {u[social_point]:d}\n"
          "    Max LP: {u[energy_max]:d}, Max # of cards: {u[unit_max]:d}, "
          "Max # of friends: {u[friend_max]:d}"
          .format(u=userinfo['response_data']['user']))
    
    client.personalnotice()
    
    tosstate = client.toscheck()
    if not tosstate['response_data']['is_agreed']:
        # Insert wait here: agreeing to TOS
        print('Agreeing to new TOS...')
        time.sleep(random.uniform(1,3))
        client.tosagree(tosstate['response_data']['tos_id'])
    
    connectstate = client.checkconnectedaccount()
    if connectstate['response_data']['is_connected']:
        print('    This account is connected to G+')
    
    print('Acquiring login bonuses...')
    client.lbonus()
    
    #client.handle_webview_get_request('/webview.php/announce/index?0=')
    print('If a browser window/tab is not opened automatically, navigate your '
          'browser to http://127.0.0.1:25252/webview.php/announce/index?0= to '
          'view notices.')
    myserver = HTTPServer(('127.0.0.1', 25252), llsifproxyhandler)
    myserver.llsifclient = client
    t = threading.Thread(target=serve_notices, args=(myserver,), daemon=True)
    t.start()
    webbrowser.open_new_tab('http://127.0.0.1:25252/webview.php/announce/index?0=')
    
    input('Press Enter to continue...')
    myserver.shutdown()
    client.session['wv_header'] = None
    
    allinfo = client.startup_api_calls()
    print('    You have {:d} present(s) in your present box.'
          .format(allinfo['response_data'][0]['result']['present_cnt']))
    
    print('All done.')
    input('Press Enter to continue...')

def serve_notices(myserver):
    myserver.serve_forever()

class llsifproxyhandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if 'favicon.ico' in self.path:
            self.send_response(404)
            self.end_headers()
            return
        
        client = self.server.llsifclient
        respstatus, respheaders, respbody = client.handle_webview_get_request(self.path)
        headers = dict(respheaders)
        
        self.send_response(respstatus)
        for headeritem in ['Content-Type', 'Content-Encoding']:
            if headeritem in headers:
                self.send_header(headeritem, headers[headeritem])
        self.send_header('Content-Length', len(respbody))
        self.end_headers()
        self.wfile.write(respbody)
        return

if __name__ == '__main__':
    main_cmdline()