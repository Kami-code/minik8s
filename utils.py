import logging
import random
import subprocess


def generate_random_str(randomlength=16, opts=0):
    """
    :param randomlength: the length of return string value
    :param opts: 0 for char + num, 1 for char only, 2 for num only
    :return: a random string with fixed length
    """
    random_str = ''
    base_str_upper_char = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    base_str_lower_char = 'abcdefghijklmnopqrstuvwxyz'
    base_str_num = '0123456789'
    base_str = ''
    if opts == 0:
        base_str = base_str_upper_char + base_str_lower_char + base_str_num
    elif opts == 1:
        base_str = base_str_upper_char + base_str_lower_char
    elif opts == 2:
        base_str = base_str_num
    else:
        logging.warning("In function generate_random_str() parameter opts should be 0/1/2...")
    base_length = len(base_str) - 1
    for i in range(randomlength):
        random_str += base_str[random.randint(0, base_length)]
    return random_str


def exec_command(command):
    logging.info("Execute Command > " + ' '.join(command))
    p = subprocess.Popen(command, stdout=subprocess.PIPE)
    output, err = p.communicate()
    if str(output, 'utf-8') != "":
        logging.info("output: %s" % str(output))
    if err is not None:
        logging.info("err: %s" % str(err))


def dump_iptables():
    """sudo iptables -X"""
    command = ["sudo", "iptables", "-X"]
    exec_command(command)


def append_rule(table, chain, rulespec, target_extension):
    """ sudo iptables -t <table> -A <chain> <rule-specification>"""
    command = ["sudo", "iptables", "-t", table, "-A", chain] + rulespec + target_extension
    exec_command(command)


def delete_rule(table, chain, rulespec, target_extension):
    """ sudo iptables -t <table> -D <chain> <rule-specification>"""
    command = ["sudo", "iptables", "-t", table, "-D", chain] + rulespec + target_extension
    exec_command(command)


def insert_rule(table, chain, rulenum, rulespec, target_extension):
    """ sudo iptables -t <table> -I <chain> <rulenum> <rule-specification>"""
    command = ["sudo", "iptables", "-t", table, "-I", chain, str(rulenum)] + rulespec + target_extension
    exec_command(command)


def replace_rule(table, chain, rulenum, rulespec, target_extension):
    """sudo iptables -t <table> -R <chain> <rulenum> <rule-specification>"""
    command = ["sudo", "iptables", "-t", table, "-R", chain, rulenum] + rulespec + target_extension
    exec_command(command)


def clear_rules():
    """sudo iptables -F"""
    command = ["sudo", "iptables", "-F"]
    exec_command(command)


def list_chain(table, chain=""):
    """sudo iptables -t <table> -n -L <chain>"""
    command = ["sudo", "iptables", "-t", table, "-L", chain]
    exec_command(command)


def flush_chain(table, chain=""):
    command = ["sudo", "iptables", "-t", table, "-F", chain]
    exec_command(command)


def create_chain(table, chain):
    """ sudo iptables -t <table> -N <chain> """
    command = ["sudo", "iptables", "-t", table, "-N", chain]
    exec_command(command)


def delete_chain(table, chain):
    """ sudo iptables -t <table> -X <chain> """
    command = ["sudo", "iptables", "-t", table, "-X", chain]
    exec_command(command)


def policy_chain(table, chain, target):
    """sudo iptables -t <table> -P <chain> <target>"""
    command = ["sudo", "iptables", "-t", table, "-P", chain] + target
    exec_command(command)


def rename_chain(table, old_chain, new_chain):
    """sudo iptables -t <table> -E <old-chain> <new-chain>"""
    command = ["sudo", "iptables", "-t", table, "-E", old_chain, new_chain]
    exec_command(command)


def get_help():
    """sudo iptables -h"""
    command = ["sudo", "iptables", "-h"]
    exec_command(command)


def make_rulespec(protocol=None, dport=None,
                  source=None, destination=None, jump=None,
                  out_interface=None, comment=None):
    """
    Make up a rule specification ( as used in the add, delete, insert, replace and append command )
    reference to: https://linux.die.net/man/8/iptables
    :param protocol: default: all, tcp/udp/icmp/all
    :param dport: destination port or port range specification
    :param source: default: 0.0.0.0/0, a network name, a hostname, a network IP address or a plain IP address
    :param destination: default: 0.0.0.0/0, destination specification
    :param jump: a user-defined chain or one of the special builtin targets (ACCEPT, DROP...)
    :param out_interface: name of an interface via which a packet is going to be sent
    :param comment: just comments, you know
    :return: A format rule-specification string like '-p tcp -s 10.0.0.0'
    """
    rulespec = []
    if protocol is not None:
        rulespec.append("-p")
        rulespec.append(protocol)
        if dport is not None:
            rulespec.append("--dport")
            rulespec.append(str(dport))
    if source is not None:
        rulespec.append("-s")
        rulespec.append(source)
    if destination is not None:
        rulespec.append("-d")
        rulespec.append(destination)
    if jump is not None:
        rulespec.append("-j")
        rulespec.append(jump)
    if out_interface is not None:
        rulespec.append("-o")
        rulespec.append(out_interface)
    if comment is not None:
        rulespec.append("-m")
        rulespec.append("comment")
        rulespec.append("--comment")
        rulespec.append(comment)
    return rulespec


def make_target_extensions(to_destination=None, mark=None, match=None, mode=None,
                           probability=None, every=None, packet=None,
                           ctstate=None, ormark=None, addrtype=None,
                           dst_type=None, statistic=None):
    """
    Make target extensions
    reference to: https://linux.die.net/man/8/iptables
    :param to_destination: This allows you to DNAT connections in a round robin way
                            over a given range of destination address
    :param mark: Set connection mark
    :param match: 
    :param mode: policy mode, random
    :param probability: used for nginx load balancing random
    :param every: used for nginx load balancing nth, every packet
    :param packet: used for nginx load balancing nth, start packet
    :param ctstate: a comma separated list of the connection states to match, INVALID/ESTABLISHED/NEW/RELATED/SNAT/DNAT
    :param ormark: perform bitwise 'or' on the IP address and this mask
    :param addrtype: address type
    :param dst_type: matches if the destination address is of given type
    :param statistic:
    :return: a format target extension string like '--to-destination 192.168.1.1:80 --set-mark 0x8888'
    """
    target = []
    if to_destination is not None:
        target.append("--to-destination")
        target.append(to_destination)
    if mark is not None:
        target.append("-m")
        target.append("mark")
        target.append("--mark")
        target.append(mark)
    if match is not None:
        target.append("-m")
        target.append(match)
    if statistic is not None:
        target.append('-m')
        target.append('statistic')
    if mode is not None:
        target.append("--mode")
        target.append(mode)
        if probability is not None:
            target.append("--probability")
            target.append(str(probability))
        if every is not None:
            target.append("--every")
            target.append(str(every))
            if packet is not None:
                target.append("--packet")
                target.append(str(packet))
    if ctstate is not None:
        target.append("-m")
        target.append("conntrack")
        target.append("--ctstate")
        target.append(ctstate)
    if ormark is not None:
        target.append("--or-mark")
        target.append(ormark)
    if addrtype is not None:
        target.append("-m")
        target.append("addrtype")
        if dst_type is not None:
            target.append("--dst-type")
            target.append(dst_type)

    return target
