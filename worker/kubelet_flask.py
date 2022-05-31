import logging
import os
import sys
from flask import Flask, request
import json
from werkzeug.utils import secure_filename
import kubeproxy
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, '../helper'))
sys.path.append(os.path.join(BASE_DIR, '../worker'))
import utils, const, yaml_loader
import psutil
import requests
import time
import entities


app = Flask(__name__)
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)


# CORS(app, supports_credentials=True)

node_instance_name = os.popen(r"ifconfig | grep -oP 'HWaddr \K.*' | sed 's/://g' | sha256sum | awk '{print $1}'")
node_instance_name = node_instance_name.readlines()[0][:-1]
node_instance_name = node_instance_name + utils.getip()

pods = list()

api_server_url = const.api_server_url
worker_port = const.worker_url_list[0]['port']
worker_url = const.worker_url_list[0]['url']
init: bool = False
heart_beat_activated = False

def get_pod_by_name(instance_name: str):
    index = -1
    pod: entities.Pod = None
    for i in range(len(pods)):
        if pods[i].instance_name == instance_name:
            index = i
            pod = pods[i]
            break
    return index, pod


@app.route('/cmd', methods=['POST'])
def execute_cmd():
    json_data = request.json
    config: dict = json.loads(json_data)
    cmd = config['cmd']
    utils.exec_command(cmd, True)
    return json.dumps(dict()), 200


@app.route('/update_services/<string:behavior>', methods=['POST'])
def update_services(behavior: str):
    print("Update Service %s" % behavior)
    json_data = request.json
    config: dict = json.loads(json_data)
    service_config = config['service_config']
    pods_dict = config['pods_dict']
    global init
    if init is False:
        init = True
        kubeproxy.init_iptables()

    if behavior == 'create':
        kubeproxy.sync_service(service_config, pods_dict)
    elif behavior == 'update':
        kubeproxy.sync_service(service_config, pods_dict)
    elif behavior == 'remove':
        kubeproxy.rm_service(service_config)
    return json.dumps(service_config), 200


@app.route('/ServerlessFunction/<string:instance_name>/upload', methods=['POST'])
def upload_script(instance_name: str):
    # todo : add serverless logic here
    config = json.loads(request.json)
    print(config)
    data = config['script_data']
    print(request.files)
    f = open('./tmp/' + secure_filename('{}.py'.format(module_name)), 'w')
    f.write(data)
    f.close()
    os.system("cd tmp && docker build . -t {}".format(module_name))
    # import docker
    #
    # docker_client = docker.from_env(version='1.25', timeout=5)
    # docker_client.images.build(path="./tmp")
    # we will build a docker image with tag: <instance_name>:latest here
    return 'file uploaded successfully'

@app.route('/Pod', methods=['POST'])
def handle_Pod():
    config: dict = json.loads(request.json)

    print("get broadcast ", config)
    # config中不含node或者node不是自己都丢弃
    if not config.__contains__('node') or config['node'] != node_instance_name\
            or not config.__contains__('behavior'):
        return "Not found", 404
    bahavior = config['behavior']
    config.pop('behavior')
    instance_name = config['instance_name']
    if bahavior == 'create':
        print("接收到调度请求 Pod")
        # 是自己的调度，进行操作
        if config.__contains__('script_data'):
            # serverless Pod
            import helper.const
            # todo : handle it with different worker url
            module_name = config['metadata']['labels']['module_name']
            r = requests.post(url=const.worker0_url + '/ServerlessFunction/{}/upload'.format(module_name), json=json.dumps(config))
            print("response = ", r.content.decode())
        pods.append(entities.Pod(config))
        print('{} create pod {}'.format(node_instance_name, instance_name))
        # share.set('status', str(status))
    elif bahavior == 'remove':
        print('try to delete Pod {}'.format(instance_name))
        index, pod = get_pod_by_name(instance_name)
        if index == -1:  # pod not found
            return "Not found", 404
        pods.pop(index)
        pod.remove()
    elif bahavior == 'execute':
        # todo: check the logic here
        print('try to execute Pod {} {}'.format(instance_name, config['cmd']))
        index, pod = get_pod_by_name(instance_name)
        print(pod)
        cmd = config['cmd']
        pod.exec_run(cmd)
    return "Success", 200


def init_node():
    # load node yaml
    yaml_name = 'master.yaml'
    yaml_path = '/'.join([BASE_DIR, 'nodes_yaml', yaml_name])
    nodes_info_config: dict = yaml_loader.load(yaml_path)
    logging.info(nodes_info_config)
    ETCD_NAME = nodes_info_config['ETCD_NAME']
    ETCD_IP_ADDRESS = nodes_info_config['IP_ADDRESS']
    ETCD_INITIAL_CLUSTER = nodes_info_config['ETCD_INITIAL_CLUSTER']
    ETCD_INITIAL_CLUSTER_STATE = nodes_info_config['ETCD_INITIAL_CLUSTER_STATE']

    cmd1 = ['bash', const.ETCD_SHELL_PATH, ETCD_NAME, ETCD_IP_ADDRESS,
            ETCD_INITIAL_CLUSTER, ETCD_INITIAL_CLUSTER_STATE]
    cmd2 = ['bash', const.FLANNEL_SHELL_PATH]
    cmd3 = ['bash', const.DOCKER_SHELL_PATH]
    utils.exec_command(cmd1, shell=False, background=True)
    logging.warning('Please make sure etcd is running successfully, waiting for 5 seconds...')
    time.sleep(5)
    utils.exec_command(cmd2, shell=False, background=True)
    logging.warning('Please make sure flannel is running successfully, waiting for 3 seconds...')
    time.sleep(3)
    utils.exec_command(cmd3, shell=False, background=True)
    logging.warning('Please make sure docker is running sucessfully, waiting for 3 seconds...')
    time.sleep(3)


    # delete original iptables and restore, init for service and dns
    dir = const.dns_conf_path
    for f in os.listdir(dir):
        if f != 'default.conf':
            os.remove(os.path.join(dir, f))
    iptable_path = os.path.dirname(os.path.realpath(__file__)) + "/sources/iptables"
    utils.exec_command(command="echo \"127.0.0.1 localhost\" > /etc/hosts", shell=True)
    utils.exec_command(command="iptables-restore < {}".format(iptable_path), shell=True)

    # todo: add other logic here
    # todo: recover pods here

    # os.system('docker stop $(docker ps -a -q)')
    # os.system('docker rm $(docker ps -a -q)')
    data = psutil.virtual_memory()
    total = data.total  # 总内存,单位为byte
    free = data.available  # 可用内存
    memory_use_percent = (int(round(data.percent)))
    cpu_use_percent = psutil.cpu_percent(interval=1)
    # print(data, total, free, memory, cpu_use_percent)

    config: dict = {'instance_name': node_instance_name, 'kind': 'Node', 'total_memory': total,
                    'cpu_use_percent': cpu_use_percent, 'memory_use_percent': memory_use_percent,
                    'free_memory': free}
    url = "{}/Node".format(api_server_url)
    json_data = json.dumps(config)
    r = requests.post(url=url, json=json_data)
    if r.status_code == 200:
        print("kubelet节点注册成功")
    else:
        print("kubelet节点注册失败")
        exit()



@app.route('/heartbeat', methods=['GET'])
def send_heart_beat():
    # should be activated once
    global heart_beat_activated
    if heart_beat_activated:
        return "Done!", 200
    heart_beat_activated = True
    while True:
        time.sleep(5)   # wait for 5 seconds
        data = psutil.virtual_memory()
        total = data.total  # 总内存,单位为byte
        free = data.available  # 可用内存
        memory_use_percent = (int(round(data.percent)))
        cpu_use_percent = psutil.cpu_percent(interval=None)
        config: dict = {'instance_name': node_instance_name, 'kind': 'Node', 'total_memory': total,
                        'cpu_use_percent': cpu_use_percent, 'memory_use_percent': memory_use_percent,
                        'free_memory': free, 'status': 'Running', 'pod_instances': list()}
        for pod in pods:
            pod_status_heartbeat = dict()
            pod_status = pod.get_status()
            # todo : get status one by one is very slow
            print("pod_status = ", pod_status)
            pod_status_heartbeat['instance_name'] = pod.instance_name
            pod_status_heartbeat['status'] = pod_status['status']
            pod_status_heartbeat['cpu_usage_percent'] = pod_status['cpu_usage_percent']
            pod_status_heartbeat['memory_usage_percent'] = pod_status['memory_usage_percent']
            pod_status_heartbeat['ip'] = pod_status['ip']
            config['pod_instances'].append(pod.instance_name)
            config[pod.instance_name] = pod_status_heartbeat

        url = "{}/heartbeat".format(api_server_url)
        json_data = json.dumps(config)
        r = requests.post(url=url, json=json_data)
        if r.status_code == 200:
            print("发送心跳包成功")
        else:
            print("发送心跳包失败")


def main():
    init_node()
    app.run(host='0.0.0.0', port=worker_port, processes=True)


if __name__ == '__main__':
    main()