from locust import HttpUser, TaskSet, task
from kubernetes import client, config
import redis
import socket

class RedisSentinelTaskSet(TaskSet):
    def on_start(self):
        self.k8s_config = config.load_incluster_config()  # Assumes you're running in a Kubernetes pod

    def get_redis_sentinel_info(self):
        v1 = client.CoreV1Api()
        sentinel_service_name = "int-redis-tester"  # Change this to your Redis Sentinel service name
        # namespace = "your-namespace"  # Change this to your Kubernetes namespace

        # service_info = v1.read_namespaced_service(name=sentinel_service_name, namespace=namespace)
        service_info = v1.read_namespaced_service(name=sentinel_service_name)

        sentinel_hosts = []
        for endpoint in service_info.spec.ports:
            sentinel_hosts.append(
                {
                    "host": socket.gethostbyname(endpoint.name),
                    "port": endpoint.port,
                    # "password": "your_sentinel_password",  # Change this to your Redis Sentinel password
                }
            )

        return sentinel_hosts

    def connect_sentinel(self):
        sentinel_hosts = self.get_redis_sentinel_info()
        self.sentinel = redis.StrictRedis(
            host=sentinel_hosts[0]['host'],
            port=sentinel_hosts[0]['port'],
            # password=sentinel_hosts[0]['password'],
            db=0,
            decode_responses=True,
        )

    def get_master(self):
        self.master = self.sentinel.sentinel_master("mymaster")  # Change this to your master service name
        return self.master

    def get_redis_connection(self, host, port, password=None, db=0):
        return redis.StrictRedis(
            host=host,
            port=port,
            # password=password,
            db=db,
            decode_responses=True,
        )

    @task(1)
    def read_value_from_redis(self):
        master_instance = self.get_master()
        master_redis = self.get_redis_connection(
            host=master_instance['ip'],
            port=master_instance['port'],
            # password="your_master_redis_password",  # Change this to your master Redis password
        )
        value = master_redis.get("example_key")
        print("Value from master:", value)

    @task(1)
    def write_value_to_redis(self):
        master_instance = self.get_master()
        master_redis = self.get_redis_connection(
            host=master_instance['ip'],
            port=master_instance['port'],
            # password="your_master_redis_password",  # Change this to your master Redis password
        )
        master_redis.set("example_key", "example_value")

class RedisSentinelK8sLoadTest(HttpUser):
    tasks = [RedisSentinelTaskSet]
    min_wait = 1000
    max_wait = 5000
