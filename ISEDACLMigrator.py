#####################################################################
'''
    Migrate DACLS from one ISE deployment to another.

    Only supports IPv4 DACLs
'''
#####################################################################

import requests
import urllib3
import json
import getpass
from colorama import Fore, Back, Style
import re
class ISE_Session():


    def __init__(self):
        self.USERNAME = ''
        self.PASSWORD = ''
        self.BASE_URL = ''
        self.SESSION = requests.Session()
        self.SESSION_COOKIE = ''
        self.HEADERS = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def set_api_creds(self, username, password):
        '''
        Set the username and password for your ISE api session.  
        Can use if you don't want to be prompted for username and password.
        :arg: str - Username
        :arg: str - password
        :return: boolean
        '''
        self.USERNAME = username
        self.PASSWORD = password
        return True
    

    def set_base_url(self, url):
        ''''
        Enter ISE base url.  You can hard code a URL so you don't have to type it out this way
        :return:
        '''
        self.BASE_URL = url
        return

    
    def enter_api_creds(self):
        '''
        Provides a prompt to enter usename and password
        Sets the session variables accordingly
        :return: 
        '''
        self.USERNAME = input('Enter Username: ')
        self.PASSWORD = getpass.getpass()
    

    def create_session(self):
        '''
        Create authenticated session object
        :return:
        '''
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        try:
            if self.USERNAME != '' and self.PASSWORD != '':
                auth_response = self.SESSION.post(self.BASE_URL + '/ers/login', auth=(self.USERNAME, self.PASSWORD), headers=headers, verify=False)
                if auth_response.status_code == 200:
                    print(f'User {self.USERNAME} has been successfully authenticated!')
                    return True
                else:
                    print(f'{Fore.LIGHTRED_EX}Something Failed\n{auth_response.status_code}\n{auth_response.reason}')
                    return False

            else:
                print('Provide API credentials')
                quit()
        except Exception as e:
            print(e)

    def get_dacls(self):
        '''
        ERS call to get a list of DACL object IDs
        :return: list
        '''
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        dacl_ids = []
        url = self.BASE_URL + '/ers/config/downloadableacl'

        try:
            response = self.SESSION.get(url, auth=(self.USERNAME, self.PASSWORD), headers=headers, verify=False)
            if response.status_code == 200:
                src_dacl_list = json.loads(response.text)

                for i in src_dacl_list['SearchResult']['resources']:
                    dacl_ids.append(i['id'])
                return dacl_ids
            elif response.status_code == 401:
                print(f'{Fore.LIGHTRED_EX}User {self.USERNAME} is unauthorized.  Contact your ISE admin or retype password\nQuitting...')
                quit()
        except requests.exceptions.InvalidSchema as e:
            print(f'\n{Fore.LIGHTRED_EX}{e}\nQuitting...')
            quit()
        except requests.exceptions.MissingSchema as e:
            print(f'\n{Fore.LIGHTRED_EX}{e}\nQuitting...')
            quit()
        except json.decoder.JSONDecodeError as e:
            print(f'{Fore.LIGHTRED_EX}Error reading output from host {self.BASE_URL}.  Try fixing URL.')
            quit()
        except Exception as e:
            print(f'{Fore.LIGHTRED_EX}{e}\nQuitting...')
            quit()
        

    def get_dacl_data(self, id_list):
        '''
        Pulls down DACL data and returns a list of DACL dicationaries for upload
        :arg: id_list - a list of DACL object IDs.
        :return: list
        '''
        my_dacls = []
        for i in id_list:
            url = self.BASE_URL + '/ers/config/downloadableacl/' + i

            try:
                response = self.SESSION.get(url, auth=(self.USERNAME, self.PASSWORD), headers=self.HEADERS, verify=False)
                dacl = json.loads(response.text)
                del dacl['DownloadableAcl']['id']
                my_dacls.append(dacl)
            except Exception as e:
                print(f'{Fore.LIGHTRED_EX}{e}Quitting...')
                quit()
        return my_dacls
    

    def post_dacl(self, dacl):
        '''
        ERS api call to post a DACL.
        :arg: dict - DACL payload data
        :return: boolean
        '''
        url = self.BASE_URL + '/ers/config/downloadableacl'
        try:
            response = self.SESSION.post(url, auth=(self.USERNAME, self.PASSWORD), headers=self.HEADERS, verify=False, data=dacl)
            if response.status_code == 201:
                dacl_name = re.search('"name":."(\S+)"',  dacl)
                dacl_name = dacl_name.group(1)
                print(f'{Fore.LIGHTGREEN_EX}Created DACL: {dacl_name}{Style.RESET_ALL}')
                return True
            elif response.status_code == 500:
                my_response = json.loads(response.text)
                message = my_response['ERSResponse']['messages'][0]['title']
                my_message = re.search("NAC.Group:NAC:dAcls:(\S+)'", message)
                my_message = my_message.group(1)
                print(f'{Fore.LIGHTYELLOW_EX}{my_message} already exists.{Style.RESET_ALL}')
                return False 
        except Exception as e:
            print(e)
            quit()
 
if __name__ == '__main__':
    
    # Disable urllib3 warnings
    urllib3.disable_warnings()

    #Welcome Screen
    print('\n\n')
    print(f'{Fore.CYAN}{Style.BRIGHT}-' * 100)
    print('\nWelcome to the DACL Migrator!\nMigrate DACLs from one ISE installation to another utilizing the ISE ERS API.\n')
    print('-' * 100 + f'\n\n{Style.RESET_ALL}')

    # Set up source ISE Deployment
    src_sess = ISE_Session()
    # Get source ISE URL
    print(f'{Fore.LIGHTYELLOW_EX}Please be sure to add your ERS ports to the URL.  \nEx. https://isepan.domain.com:9060\n\n')
    src_sess.set_base_url(url=input(f'{Fore.LIGHTWHITE_EX}Source URL: '))
    #src_sess.set_base_url('https://ise2.batcave.com:9060')
    # Get creds for the source ISE
    print('\nEnter Credentials for source ISE')
    src_sess.enter_api_creds()

    dacl_list = src_sess.get_dacls()
    # dacls is all of the dacls, ready to be added to the destination ISE deployment
    dacls = src_sess.get_dacl_data(dacl_list)
    

    # Set up destination ISE deployment
    print('\n\n')
    dest_sess = ISE_Session()
    
    dest_sess.set_base_url(url=input(f'{Fore.LIGHTGREEN_EX}Destination URL: {Style.RESET_ALL}'))
    #dest_sess.set_base_url('https://ise1.batcave.com:9060')
    dest_sess.enter_api_creds()
    # Verification
    print('-' * 100)
    print(f'Source ISE: {Fore.LIGHTMAGENTA_EX}{src_sess.BASE_URL}{Style.RESET_ALL}   ---->   Destination ISE: {Fore.LIGHTGREEN_EX}{dest_sess.BASE_URL}{Style.RESET_ALL}')
    proceed = input('Migrate ACLs? (Y/N)')
    if proceed.capitalize() == 'Y':
        pass
    else:
        print('Quitting')
        quit()
    print('-'* 50)
    print(f'Attempting to create {dacls.__len__()} DACLs.')
    counter = 0
    for i in dacls:
        my_dacl = json.dumps(i)
        if dest_sess.post_dacl(my_dacl) == True:
            counter +=1 
    
    print('-'* 50)
    print(f'{Fore.LIGHTGREEN_EX}Created {counter} DACLs on {dest_sess.BASE_URL}')
    print('-'* 50)

