import jinja2
import os
from sys import argv
import re

# TODO: pull server key from specific conf
# TODO: argparse

CONF_PATH = "/etc/wireguard/wg0.conf" # TODO: get from argv
ALLOWED_IPS_PREFIX = re.compile(r"AllowedIPs\s+=\s+")
IP_REGEX = re.compile(r"((?:\d+\.)+)(\d+)(\/\d+)")
PRIVATE_KEY_PATH = ".privatekey"
PUBLIC_KEY_PATH = ".publickey"
PSK_PATH = ".psk"


def generate_keys():
    os.system(f"wg genkey | tee {PRIVATE_KEY_PATH} | wg pubkey | tee {PUBLIC_KEY_PATH} > /dev/null && wg genpsk > {PSK_PATH}")
    res = []
    for path in [PRIVATE_KEY_PATH, PUBLIC_KEY_PATH, PSK_PATH]:
        with open(path, "r", encoding="utf-8") as inf:
            res.append(inf.readline())
            os.system(f"rm -rf {path}")

    return res

# find last ip
with open(CONF_PATH, "r", encoding="utf-8") as server_conf_file:
    sorted_ips = list(sorted(map(lambda line: ALLOWED_IPS_PREFIX.sub("", line).replace(" ", ""), filter(lambda line: "AllowedIPs" in line, server_conf_file.readlines())), reverse=True, key=lambda ip_str : int(ip_str[ip_str.rfind(".")+1:ip_str.rfind("/")])))
    max_ip = sorted_ips[0]

last_ip_seg = int(IP_REGEX.match(max_ip).group(2)) + 1
print(f"new {last_ip_seg=}")

next_ip = IP_REGEX.sub(rf"\g<1>{last_ip_seg}", max_ip).replace("\n", "")
private_key, public_key, psk = generate_keys()

# generate configs
environment = jinja2.Environment(loader=jinja2.FileSystemLoader("templates/"))
client_template = environment.get_template("client_configuration.config")
server_template = environment.get_template("server_configuration.config")
client_conf = client_template.render(
    next_ip=f"{next_ip}/24\n",
    private_peer_key=private_key,
    preshared_key=psk
) + "\n"

server_conf = server_template.render(
    public_peer_key=public_key,
    preshared_key=psk,
    next_ip=f"{next_ip}/32\n"
) + "\n"

client_conf_path = f"{argv[1]}.conf"
with open(client_conf_path, "w", encoding="utf-8") as client_conf_file:
    client_conf_file.write(client_conf)
    # print(client_conf)

with open(CONF_PATH, "a", encoding="utf-8") as server_conf_file:
    server_conf_file.write(server_conf)
    # print(server_conf)

os.system(f"qrencode -t ansiutf8 < {client_conf_path}")
os.system(f"cp {client_conf_path} /root")
os.system(f"systemctl restart wg-quick@wg0")
print(f"added ip is {next_ip}")
