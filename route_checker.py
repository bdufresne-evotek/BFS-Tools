import ipaddress
import getpass
from netmiko import ConnectHandler, NetMikoTimeoutException, NetMikoAuthenticationException

def main():
    creds_valid = False
    while not creds_valid: # Loop as long as creds_valid is False
        creds = get_credentials()  # Initialize creds at the start
        device_info = set_deviceInfo(creds)
        creds_valid = test_credentials(device_info)
        
    while creds_valid:  # Loop as long as creds_valid is True
        device_info = set_deviceInfo(creds)
        print("Enter subnet to look up - Example: 10.0.1.0/24")
        network = input("Subnet: ")
        net_result = check_ip(network)
        
        if net_result.split(':')[0] == "Warn":
            print(net_result)
            result = check_route(network, device_info)
            
        elif net_result.split(':')[0] == "Ok":
            result = check_route(network, device_info)
        
        else:
            print(net_result)
            net_result = ''
            print_color('Starting over..', 'red')
            
        if net_result:
            if isinstance(result, list) and len(result) > 0:
                routeEntry = {
                    'protocol': result[0]['protocol'],
                    'network': result[0]['network'],
                    'mask': result[0]['mask'],
                    'distance': result[0]['distance'],
                    'metric': result[0]['metric'],
                    'nexthop_ip': result[0]['nexthop_ip'],
                    'nexthop_if': result[0]['nexthop_if'],
                    'uptime': result[0]['uptime']
                }

                if routeEntry['nexthop_ip']:
                    print_color(f"Network found in routing table!\n", 'green')
                    print(routeEntry)
                else:
                    print_color("Network not found in routing table!", 'red')
                    if routeEntry['nexthop_if'] == 'Null0':
                        print_color(f"Route is black-holed (Null0) - {routeEntry['network']}/{routeEntry}", 'yellow')
                    print(routeEntry)
            else:
                print_color("No valid routes found or an error occurred.", 'red')
    
        print('==============================\nPress Ctrl+C or close window to stop\n==============================\n')

def get_credentials():
    username = ''
    password = ''
    creds = {}
    username = input("Enter TACACs username: ")
    password = getpass.getpass(prompt="Enter TACACs password: ")
    creds = {
        'exists': True,
        'username': username,
        'password': password
    }
    return creds

def set_deviceInfo(creds):
    device_info = {
        'device_type': 'cisco_nxos',
        'ip': '172.30.48.14',  # IP for TXGRLD-ED01
        'username': creds['username'],
        'password': creds['password']
    }
    return device_info

def test_credentials(device_info):
    try:
        # Attempt connection
        connection = ConnectHandler(**device_info)
        hostname = connection.find_prompt().strip('#<>[]')
        connection.disconnect()

        if hostname:
            print_color('Credentials valid', 'green')
            return True  # Authentication and connection successful
        else:
            print(hostname)
            print_color('Something may be wrong with the connection', 'yellow')
            return False

    # Specific exception for authentication failure
    except NetMikoAuthenticationException:
        print_color(f"Error: Authentication failed for {device_info['ip']}.", 'red')
        return False
    
    # Specific exception for connection timeout
    except NetMikoTimeoutException:
        print_color(f"Error: Connection to {device_info['ip']} timed out.", 'red')
        return False

    # Generic exception for any other issue
    except Exception as e:
        print_color(f"Error: Unable to connect to {device_info['ip']} - {str(e)}", 'red')
        return False


def check_ip(network):
    try:
        if '/' in network:
            net = network.split("/")[0]
            mask = network.split("/")[1]
            if mask == '24':
                target = ipaddress.ip_network(network, strict=False)
                return f"Ok: {target}"
            elif mask != '24':
                print_color(f"Warn: Network entered [{net}] is [{mask}] not a /24 - verify results.", 'yellow')
                return f"Warn: {target}"
        else:
            target = ipaddress.ip_network(f"{network}/24", strict=False)
            return f"Ok: {target}"
    except ValueError as ve:
        return f"Error: {ve}"
    
def check_route(network, device_info):
    try:
        connection = ConnectHandler(**device_info)
        hostname = connection.find_prompt().strip('#<>[]')
        print(f"Connected to {hostname}")
        route_result = connection.send_command(f'show ip route {network}', use_textfsm=True)
        print(f"Sent: show ip route {network}")
        connection.disconnect()
        return route_result
    
    except Exception as e:
        print_color(f"Warn: Unable to connect to {device_info['ip']}", 'yellow')
        return e

def print_color(text, color):
    # ANSI escape codes for colors and bold formatting
    colors = {
        'green': '\033[1;32m',  # Bold Green
        'yellow': '\033[33m',        # Yellow
        'red': '\033[1;31m'     # Bold Red
    }
    reset = '\033[0m'  # Reset formatting

    # Check if color is valid, else default to reset
    if color in colors:
        print(f"{colors[color]}{text}{reset}")
    else:
        print(text)

if __name__ == "__main__":
    main()