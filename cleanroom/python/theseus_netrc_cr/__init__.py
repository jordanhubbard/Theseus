"""
theseus_netrc_cr: Clean-room netrc file parser.
"""

import os
import shlex


def parse_netrc(text):
    """
    Parse netrc format text string.
    Returns a dict mapping host -> (login, account, password).
    """
    hosts = {}
    
    # Tokenize using shlex to handle quoted strings and comments
    try:
        tokens = shlex.split(text, comments=True)
    except ValueError:
        # Fall back to simple splitting if shlex fails
        tokens = text.split()
    
    i = 0
    while i < len(tokens):
        token = tokens[i]
        
        if token == 'machine':
            if i + 1 >= len(tokens):
                break
            host = tokens[i + 1]
            i += 2
            
            login = None
            account = None
            password = None
            
            # Parse key-value pairs until next machine/default/macdef
            while i < len(tokens):
                key = tokens[i]
                if key in ('machine', 'default', 'macdef'):
                    break
                elif key == 'login':
                    if i + 1 < len(tokens):
                        login = tokens[i + 1]
                        i += 2
                    else:
                        i += 1
                elif key == 'account':
                    if i + 1 < len(tokens):
                        account = tokens[i + 1]
                        i += 2
                    else:
                        i += 1
                elif key == 'password':
                    if i + 1 < len(tokens):
                        password = tokens[i + 1]
                        i += 2
                    else:
                        i += 1
                else:
                    i += 1
            
            hosts[host] = (login, account, password)
        
        elif token == 'default':
            i += 1
            login = None
            account = None
            password = None
            
            while i < len(tokens):
                key = tokens[i]
                if key in ('machine', 'default', 'macdef'):
                    break
                elif key == 'login':
                    if i + 1 < len(tokens):
                        login = tokens[i + 1]
                        i += 2
                    else:
                        i += 1
                elif key == 'account':
                    if i + 1 < len(tokens):
                        account = tokens[i + 1]
                        i += 2
                    else:
                        i += 1
                elif key == 'password':
                    if i + 1 < len(tokens):
                        password = tokens[i + 1]
                        i += 2
                    else:
                        i += 1
                else:
                    i += 1
            
            hosts['default'] = (login, account, password)
        
        elif token == 'macdef':
            # Skip macdef block - consume until blank line
            # In token mode, just skip the name and move on
            i += 2  # skip 'macdef' and the macro name
        
        else:
            i += 1
    
    return hosts


class netrc:
    """
    netrc file parser class.
    """
    
    def __init__(self, file=None):
        """
        Parse netrc from file path or string.
        If file is None, use ~/.netrc.
        If file is a string path that exists, read from it.
        Otherwise treat file as netrc content string.
        """
        if file is None:
            # Try to read from ~/.netrc
            home = os.path.expanduser('~')
            netrc_path = os.path.join(home, '.netrc')
            try:
                with open(netrc_path, 'r') as f:
                    text = f.read()
            except (IOError, OSError):
                text = ''
        elif isinstance(file, str) and os.path.exists(file):
            with open(file, 'r') as f:
                text = f.read()
        else:
            # Treat as content string
            text = file if isinstance(file, str) else ''
        
        self.hosts = parse_netrc(text)
    
    def authenticators(self, host):
        """
        Return (login, account, password) tuple for host.
        Returns None if host not found.
        """
        if host in self.hosts:
            return self.hosts[host]
        if 'default' in self.hosts:
            return self.hosts['default']
        return None


# Test helper functions referenced in invariants

def netrc_parse_host():
    text = 'machine example.com login user password secret'
    hosts = parse_netrc(text)
    return hosts['example.com'][0]


def netrc_parse_password():
    text = 'machine example.com login user password secret'
    hosts = parse_netrc(text)
    return hosts['example.com'][2]


def netrc_parse_two_hosts():
    text = (
        'machine example.com login user password secret\n'
        'machine other.com login admin password pass123\n'
    )
    hosts = parse_netrc(text)
    return len(hosts)