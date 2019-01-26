import configparser
from http import HTTPStatus
from datetime import datetime
from subprocess import Popen
from pathlib import Path
import pdb # for debug
import copy
from concurrent.futures import ThreadPoolExecutor

from settings.docker import CODE_SUCCESS, CODE_HAS_IMAGE, CODE_NO_IMAGE, DOCKER_BASIC_SETTINGS_PATH
from tool.common.logging.logger_factory import LoggerFactory
from tool.common.rsync import Rsync
from tool.docker.docker_layer import DockerLayer
from tool.docker.docker_container_extraction import DockerContainerExtraction
from tool.docker.docker_container_extraction import DockerVolume
from tool.gRPC.grpc_client import RpcClient
from tool.socket.remote_com_client import SmartCommunityRouterAPI, ClientMessageCode, ClientMessageCode, RemoteComClient, ClientBufInfo, ScrDirection

# for data consistency migration
from tool.redis.redis_client import RedisClient
from tool.common.extensions.rdict import rdict

# For evaluation
from tool.common.eval.time_recorder import TimeRecorder, ProposedMigrationConst, ConservativeMigrationConst, DataConsistencyMigrationConst
from tool.common.eval.resource_recorder import ResourceRecorder
from tool.common.eval.disk_recorder import DiskRecorder
from tool.common.eval.buffer_logger import BufferLogger

class MigrationWorker:
    TOTAL_STREAM_COUNT = 2
    ORDER_OF_REQUEST_MIGRATION = 2

    def __init__(self, cli, i_name, version, c_name, m_opt, c_opt, bandwidth=0, packet_rate=0):
        config = configparser.ConfigParser()
        config.read(DOCKER_BASIC_SETTINGS_PATH)
        i_layer_manager = DockerLayer()

        # Migration attributes
        self._logger = LoggerFactory.create_logger(self)
        self._d_cli = cli
        self._c_id = cli.container_presence(c_name).id
        self._d_c_extractor = DockerContainerExtraction(c_name, self._c_id,i_layer_manager.get_local_layer_ids(i_name),i_layer_manager.get_container_layer_ids(c_name))
        self._d_config = config
        self._i_name = i_name
        self._version = version
        self._c_name = c_name

        self._m_opt = m_opt
        self._c_opt = c_opt
        self._bandwidth = bandwidth
        self._packet_rate = packet_rate

    """
    Start migration-worker for migrating Docker App based on the following tasks
    1. Inspect images, pull the image if it doesn't exist
    2. Create a container (leave the app run)
    3. Create checkpoint (leave the app run)
    4. Send checkpoints to dst host
    5. Restore the App based on the data

    @return True|False
    """
    def run_llm(self):
        self._logger.info("run: Init RPC client")
        rpc_client = RpcClient(dst_addr=self._m_opt['dst_addr'])
        #d_recorder = DiskRecorder('prop_{0}_{1}'.format(self._bandwidth, self._c_name))
        #t_recorder = TimeRecorder('prop_{0}_{1}'.format(self._bandwidth, self._c_name) )
        #r_recorder = ResourceRecorder('prop_{0}_{1}'.format(self._bandwidth, self._c_name))

        #r_recorder.insert_init_cond()
        #r_recorder.track_on_subp()
        #t_recorder.track(ProposedMigrationConst.MIGRATION_TIME)

        #1. Inspect Images
        code = rpc_client.inspect(i_name=self._i_name, version=self._version, c_name=self._c_name)

        #2. checkpoint docker container
        #3. tranfer tranfer the container artifacts
        # TODO: before checkpoint, check signal is changed
        #t_recorder.track(ProposedMigrationConst.CHECKPOINT)
        #t_recorder.track(ProposedMigrationConst.SERVICE_DOWNTIME)
        has_checkpointed = self._d_cli.checkpoint(self._c_name)
        #t_recorder.track(ProposedMigrationConst.CHECKPOINT)
        if has_checkpointed is not True:
            return self.returned_data_creator('checkpoint', code=HTTPStatus.INTERNAL_SERVER_ERROR.value)
        has_create_tmp_dir = rpc_client.create_tmp_dir(self._c_id)
        if has_create_tmp_dir is not CODE_SUCCESS:
            #TODO: fix
            return self.returned_data_creator('checkpoint', code=HTTPStatus.INTERNAL_SERVER_ERROR.value)

        #t_recorder.track(ProposedMigrationConst.RSYNC_C_FS)
        has_sent = self._d_c_extractor.transfer_container_artifacts(dst_addr=self._m_opt['dst_addr'])
        #t_recorder.track(ProposedMigrationConst.RSYNC_C_FS)
        if has_sent is not True:
            return self.returned_data_creator('send_checkpoint', code=HTTPStatus.INTERNAL_SERVER_ERROR.value)

        # 5. Restore the App based on the data
        #t_recorder.track(ProposedMigrationConst.SYNC_C)
        volumes=[ volume.hash_converter() for volume in self._d_c_extractor.volumes]
        code = rpc_client.allocate_container_artifacts(self._d_c_extractor.c_name,
                                                       self._d_c_extractor.c_id,
                                                       self._d_c_extractor.i_layer_ids,
                                                       self._d_c_extractor.c_layer_ids,
                                                       volumes=volumes
                                                       )
        #t_recorder.track(ProposedMigrationConst.SYNC_C)

        #t_recorder.track(ProposedMigrationConst.RELOAD)
        code = rpc_client.reload_daemon()
        #t_recorder.track(ProposedMigrationConst.RELOAD)

        self._logger.info("Restore container at dst host")
        #t_recorder.track(ProposedMigrationConst.RESTORE)
        code = rpc_client.restore(self._c_name)
        #t_recorder.track(ProposedMigrationConst.RESTORE)

        #t_recorder.track(ProposedMigrationConst.SERVICE_DOWNTIME)
        #t_recorder.track(ProposedMigrationConst.MIGRATION_TIME)
        #r_recorder.terminate_subp()
        if code != CODE_SUCCESS:
            return self.returned_data_creator(rpc_client.restore.__name__, code=code)

        #t_recorder.write()
        #r_recorder.write()
        #d_recorder.track_all(self._d_c_extractor)
        #d_recorder.write()
        return self.returned_data_creator('fin')

    def run_involving_commit(self):
        self._logger.info("run_with_image_migration: Init RPC client")
        print("rpc_client")
        rpc_client = RpcClient(dst_addr=self._m_opt['dst_addr'])
        tag = self.tag_creator()

        src_repo = '{base}/{i_name}'.format(base=self._d_config['docker_hub']['private'],i_name=self._i_name.replace('/','_')) # avoid erro bacase of str '/'
        dst_repo = '{base}/{i_name}'.format(base=self._d_config['docker_hub']['local'],i_name=self._i_name.replace('/','_'))
        dir_name = '{0}_{1}'.format(self._i_name.replace('/','_'),tag)
        dst_default_path = '{0}/{1}'.format(self._d_config['destination']['default_dir'], dir_name)
        print(src_repo)
        print(dst_repo)

        volumes=[]
        c_volume_options = []
        print("collecti volumes")
        for vo in DockerVolume.collect_volumes(self._c_name, self._d_cli.lo_client, self._d_cli.client):
            vo_hash = vo.hash_converter()
            c_vo_hash = copy.copy(vo_hash)
            c_vo_hash['h_path'] = '{default_path}/{dir_name}'.format(default_path=dst_default_path, dir_name=Path(vo_hash['h_path']).name)
            volumes.append(vo_hash)
            c_volume_options.append(c_vo_hash)

        d_recorder = DiskRecorder('con_{0}_{1}'.format(self._bandwidth, self._c_name))
        t_recorder = TimeRecorder('con_{0}_{1}'.format(self._bandwidth, self._c_name), migration_type='conservative')
        r_recorder = ResourceRecorder('con_{0}_{1}'.format(self._bandwidth, self._c_name))

        r_recorder.insert_init_cond()
        r_recorder.track_on_subp()
        t_recorder.track(ConservativeMigrationConst.MIGRATION_TIME)

        print("commit")
        # ===============COMMIT=================
        t_recorder.track(ConservativeMigrationConst.COMMIT)
        image = self._d_cli.commit(c_name=self._c_name, repository=src_repo, tag=tag)
        t_recorder.track(ConservativeMigrationConst.COMMIT)

        if image is not None:
            self._logger.info("Push Docker repo:{0}, tag:{1}".format(src_repo, tag))

            print("push")
            # ===============PUSH=================
            t_recorder.track(ConservativeMigrationConst.PUSH)
            has_pushed = self._d_cli.push(repository=src_repo, tag=tag)
            t_recorder.track(ConservativeMigrationConst.PUSH)

            if has_pushed is False:
                return self.returned_data_creator('push')
        else:
            return self.returned_data_creator('commit')

        print("pull")
        # ===============PULL=================
        self._logger.info("Pull an image on dst")
        t_recorder.track(ConservativeMigrationConst.PULL)
        pulled_image = rpc_client.pull(i_name=dst_repo, version=tag)
        t_recorder.track(ConservativeMigrationConst.PULL)

        if pulled_image is not None:
            self._logger.info("Checkpoint running container")

            print("checkpoint")
            # ===============CHECKPOINT=================
            t_recorder.track(ConservativeMigrationConst.CHECKPOINT)
            t_recorder.track(ConservativeMigrationConst.SERVICE_DOWNTIME)
            has_checkpointed = self._d_cli.checkpoint(self._c_name, cp_name='checkpoint1', need_tmp_dir=True)
            t_recorder.track(ConservativeMigrationConst.CHECKPOINT)

            print("rsync")
            # ===============RSYNC_C=================
            t_recorder.track(ConservativeMigrationConst.RSYNC_C_FS)
            has_checkpoint_sent = self.send_checkpoint(src_repo, tag)
            has_volume_sent = self.send_volume(dst_repo, tag, volumes) if len(volumes) != 0 else True
            t_recorder.track(ConservativeMigrationConst.RSYNC_C_FS)

            if has_checkpointed is not True:
                return self.returned_data_creator('checkpoint')
            if has_checkpoint_sent is not True:
                return self.returned_data_creator('send_checkpoint')
            if has_volume_sent is not True:
                return self.returned_data_creator('volume')
        else:
            return self.returned_data_creator('create')

        print("create")
        # ===============CREATE_C=================
        t_recorder.track(ConservativeMigrationConst.CREATE_C)
        status_with_c_id = rpc_client.create_container(i_name=dst_repo, version=tag, c_name=self._c_name, volumes=c_volume_options)
        t_recorder.track(ConservativeMigrationConst.CREATE_C)

        if status_with_c_id.code ==  CODE_SUCCESS:
            self._logger.info("Restore container at dst host")
            restore_target_path = '{0}/checkpoints'.format(dst_default_path)

            print("restore")
            # ===============RESTORE=================
            t_recorder.track(ConservativeMigrationConst.RESTORE)
            code = rpc_client.restore(self._c_name, default_path=restore_target_path)
            t_recorder.track(ConservativeMigrationConst.RESTORE)
            if code != CODE_SUCCESS:
                return self.returned_data_creator(rpc_client.restore.__name__, code=code)
        else:
            return self.returned_data_creator('create')

        t_recorder.track(ConservativeMigrationConst.SERVICE_DOWNTIME)
        t_recorder.track(ConservativeMigrationConst.MIGRATION_TIME)
        r_recorder.terminate_subp()

        t_recorder.write()
        r_recorder.write()

        return self.returned_data_creator('fin')

    def run_cgm(self, app_id=0):
        self._logger.info("run: Init RPC client")
        remote_rpc_cli = RpcClient(dst_addr=self._m_opt['dst_addr'])
        local_rpc_cli = RpcClient(dst_addr='127.0.0.1')
        dst_first_packet_id =0
        src_last_packet_id =0
        dst_local_addr = self._m_opt['pkt_dst_addr']
        redis_cli = RedisClient()

        #### src app info
        app_info_dict = local_rpc_cli.get_app_info_dict(app_id)

        #### create buffer
        dst_app_id = remote_rpc_cli.prepare_app_launch(app_info_dict.buf_loc,app_info_dict.sig_loc,[str(e) for e in app_info_dict.rules])
        ### check src and dst buffer
        print("check C2S packet")
        # TODO: check behavior
        dst_first_C2S_packet_id = remote_rpc_cli.get_buf_info(dst_app_id, kind=ClientBufInfo.BUF_FIRST.value, direction=ScrDirection.C2S.value)  #in this case packet_id
        print(dst_first_C2S_packet_id)
        if (not (local_rpc_cli.check_packet_arrival(app_id, dst_first_C2S_packet_id))):
            return self.returned_data_creator('create')

        # check whether last src packet is arrived at dst node
        print("check S2C packet")
        # TODO: check behavior
        dst_first_S2C_packet_id = remote_rpc_cli.get_buf_info(dst_app_id, kind=ClientBufInfo.BUF_FIRST.value, direction=ScrDirection.S2C.value)  #in this case packet_id
        print(dst_first_S2C_packet_id)
        if (not (local_rpc_cli.check_packet_arrival(dst_app_id, dst_first_S2C_packet_id))):
            return self.returned_data_creator('create')

        ####  request ready for checkpoint
        # del buffer
        print('prepare for checkpoint')
        local_rpc_cli.prepare_for_checkpoint(app_id)

        # Inspect Images
        #code = remote_rpc_cli.inspect(i_name=self._i_name, version=self._version, c_name=self._c_name)

        # Check signal status
        print('check status')
        is_ready = local_rpc_cli.check_status(app_id)
        if is_ready is False:
            return self.returned_data_creator('check_status', code=HTTPStatus.INTERNAL_SERVER_ERROR.value)

        # Checkpoint
        print("==============checkpoint==============")
        has_checkpointed = self._d_cli.checkpoint(self._c_name)
        if has_checkpointed is not True:
            return self.returned_data_creator('checkpoint', code=HTTPStatus.INTERNAL_SERVER_ERROR.value)
        has_create_tmp_dir = remote_rpc_cli.create_tmp_dir(self._c_id)
        if has_create_tmp_dir is not CODE_SUCCESS:
            #TODO: fix
            return self.returned_data_creator('checkpoint', code=HTTPStatus.INTERNAL_SERVER_ERROR.value)

        # Send artifacts
        has_sent = self._d_c_extractor.transfer_container_artifacts(dst_addr=self._m_opt['dst_addr'])
        if has_sent is not True:
            return self.returned_data_creator('send_checkpoint', code=HTTPStatus.INTERNAL_SERVER_ERROR.value)
        volumes=[ volume.hash_converter() for volume in self._d_c_extractor.volumes]
        code = remote_rpc_cli.allocate_container_artifacts(self._d_c_extractor.c_name,
                                                       self._d_c_extractor.c_id,
                                                       self._d_c_extractor.i_layer_ids,
                                                       self._d_c_extractor.c_layer_ids,
                                                       volumes=volumes)

        # Reload daemon
        code = remote_rpc_cli.reload_daemon()

        # Update application buffer read offset
        rd = rdict(redis_cli.hgetall(app_id))
        C2S_info = {"direction": ScrDirection.C2S.value, "packet_id": rd["{0}.*{1}".format(ScrDirection.C2S.value, dst_local_addr)][0]}
        S2C_info = {"direction": ScrDirection.S2C.value, "packet_id": rd["{0}.*{1}".format(ScrDirection.S2C.value, dst_local_addr)][0]}
        code = remote_rpc_cli.update_buf_read_offset(app_id, [C2S_info, S2C_info])

        # Restore
        code = remote_rpc_cli.restore(self._c_name)
        if code != CODE_SUCCESS:
            return self.returned_data_creator(remote_rpc_cli.restore.__name__, code=code)

        return self.returned_data_creator('fin')

    def run_cgm_with_recorder(self, app_id=0):
        self._logger.info("run: Init RPC client")
        remote_rpc_cli = RpcClient(dst_addr=self._m_opt['dst_addr'])
        local_rpc_cli = RpcClient(dst_addr='127.0.0.1')
        dst_first_packet_id =0
        src_last_packet_id =0
        #dst_local_addr = "192.168.3.33" # sensor 3
        dst_local_addr = self._m_opt['pkt_dst_addr']
        redis_cli = RedisClient()

        #d_recorder = DiskRecorder('dcm_{0}_{1}'.format(self._packet_rate, self._c_name))
        #t_recorder = TimeRecorder('dcm_{0}_{1}'.format(self._packet_rate, self._c_name), migration_type="dcm")
        #r_recorder = ResourceRecorder('dcm_{0}_{1}'.format(self._packet_rate, self._c_name))
        #buf_logger = BufferLogger('dcm_{0}_{1}'.format(self._packet_rate, self._c_name),dst_addr=self._m_opt['dst_addr'])

        #r_recorder.insert_init_cond()
        #r_recorder.track_on_subp()
        #t_recorder.track(DataConsistencyMigrationConst.MIGRATION_TIME)

        #### src app info
        # Check docker_migration.proto for refering data format of app_info_dict
        #t_recorder.track(DataConsistencyMigrationConst.SRC_GET_APP_INFO)
        app_info_dict = local_rpc_cli.get_app_info_dict(app_id)
        #t_recorder.track(DataConsistencyMigrationConst.SRC_GET_APP_INFO)

        #### create buffer
        #t_recorder.track(DataConsistencyMigrationConst.DST_CREATE_BUF)
        dst_app_id = remote_rpc_cli.prepare_app_launch(app_info_dict.buf_loc,app_info_dict.sig_loc,[str(e) for e in app_info_dict.rules])
        #t_recorder.track(DataConsistencyMigrationConst.DST_CREATE_BUF)

        ### check src and dst buffer
        print("check C2S packet")
        #t_recorder.track(DataConsistencyMigrationConst.SRC_CHECK_DST_PACKET_ARRAIVAL)
        # TODO: check behavior
        dst_first_C2S_packet_id = remote_rpc_cli.get_buf_info(dst_app_id, kind=ClientBufInfo.BUF_FIRST.value, direction=ScrDirection.C2S.value)  #in this case packet_id
        print(dst_first_C2S_packet_id)
        if (not (local_rpc_cli.check_packet_arrival(app_id, dst_first_C2S_packet_id))):
            return self.returned_data_creator('create')
        #t_recorder.track(DataConsistencyMigrationConst.SRC_CHECK_DST_PACKET_ARRAIVAL)

        # check whether last src packet is arrived at dst node
        print("check S2C packet")
        #t_recorder.track(DataConsistencyMigrationConst.DST_CHECK_SRC_PACKET_ARRAIVAL)
        # TODO: check behavior
        dst_first_S2C_packet_id = remote_rpc_cli.get_buf_info(dst_app_id, kind=ClientBufInfo.BUF_FIRST.value, direction=ScrDirection.S2C.value)  #in this case packet_id
        print(dst_first_S2C_packet_id)
        if (not (local_rpc_cli.check_packet_arrival(dst_app_id, dst_first_S2C_packet_id))):
            return self.returned_data_creator('create')
        #t_recorder.track(DataConsistencyMigrationConst.DST_CHECK_SRC_PACKET_ARRAIVAL)

        ####  request ready for checkpoint
        # del buffer
        print('prepare for checkpoint')
        #t_recorder.track(DataConsistencyMigrationConst.SRC_DEL_RULES_AND_BUF)
        local_rpc_cli.prepare_for_checkpoint(app_id)
        #t_recorder.track(DataConsistencyMigrationConst.SRC_DEL_RULES_AND_BUF)


        # Inspect Images
        code = remote_rpc_cli.inspect(i_name=self._i_name, version=self._version, c_name=self._c_name)

        # Check signal status
        print('check status')
        #t_recorder.track(DataConsistencyMigrationConst.DST_CHECK_STATUS)
        is_ready = local_rpc_cli.check_status(app_id)
        if is_ready is False:
            return self.returned_data_creator('check_status', code=HTTPStatus.INTERNAL_SERVER_ERROR.value)
        #t_recorder.track(DataConsistencyMigrationConst.DST_CHECK_STATUS)

        # Checkpoint
        print("==============checkpoint==============")
        #t_recorder.track(DataConsistencyMigrationConst.CHECKPOINT)
        #t_recorder.track(DataConsistencyMigrationConst.SERVICE_DOWNTIME)
        has_checkpointed = self._d_cli.checkpoint(self._c_name)
        #t_recorder.track(DataConsistencyMigrationConst.CHECKPOINT)
        if has_checkpointed is not True:
            return self.returned_data_creator('checkpoint', code=HTTPStatus.INTERNAL_SERVER_ERROR.value)
        has_create_tmp_dir = remote_rpc_cli.create_tmp_dir(self._c_id)
        if has_create_tmp_dir is not CODE_SUCCESS:
            #TODO: fix
            return self.returned_data_creator('checkpoint', code=HTTPStatus.INTERNAL_SERVER_ERROR.value)

        # Send artifacts
        #t_recorder.track(DataConsistencyMigrationConst.RSYNC_C_FS)
        has_sent = self._d_c_extractor.transfer_container_artifacts(dst_addr=self._m_opt['dst_addr'])
        #t_recorder.track(DataConsistencyMigrationConst.RSYNC_C_FS)
        if has_sent is not True:
            return self.returned_data_creator('send_checkpoint', code=HTTPStatus.INTERNAL_SERVER_ERROR.value)
        #t_recorder.track(DataConsistencyMigrationConst.ALLOCATE_FS)
        volumes=[ volume.hash_converter() for volume in self._d_c_extractor.volumes]
        code = remote_rpc_cli.allocate_container_artifacts(self._d_c_extractor.c_name,
                                                       self._d_c_extractor.c_id,
                                                       self._d_c_extractor.i_layer_ids,
                                                       self._d_c_extractor.c_layer_ids,
                                                       volumes=volumes)
        #t_recorder.track(DataConsistencyMigrationConst.ALLOCATE_FS)

        # Reload daemon
        #t_recorder.track(DataConsistencyMigrationConst.RELOAD)
        code = remote_rpc_cli.reload_daemon()
        #t_recorder.track(DataConsistencyMigrationConst.RELOAD)

        # Update application buffer read offset
        #t_recorder.track(DataConsistencyMigrationConst.DST_UPDATE_OFFSET)
        rd = rdict(redis_cli.hgetall(app_id))
        #rd = rdict(redis_cli.hgetall(app_id))
        C2S_info = {"direction": ScrDirection.C2S.value, "packet_id": rd["{0}.*{1}".format(ScrDirection.C2S.value, dst_local_addr)][0]}
        S2C_info = {"direction": ScrDirection.S2C.value, "packet_id": rd["{0}.*{1}".format(ScrDirection.S2C.value, dst_local_addr)][0]}
        code = remote_rpc_cli.update_buf_read_offset(app_id, [C2S_info, S2C_info])
        #t_recorder.track(DataConsistencyMigrationConst.DST_UPDATE_OFFSET)

        # Restore
        #t_recorder.track(DataConsistencyMigrationConst.RESTORE)
        code = remote_rpc_cli.restore(self._c_name)
        #t_recorder.track(DataConsistencyMigrationConst.RESTORE)
        #t_recorder.track(DataConsistencyMigrationConst.SERVICE_DOWNTIME)
        #t_recorder.track(DataConsistencyMigrationConst.MIGRATION_TIME)
        #r_recorder.terminate_subp()

        if code != CODE_SUCCESS:
            return self.returned_data_creator(remote_rpc_cli.restore.__name__, code=code)

        # Write data
        #t_recorder.write()
        #r_recorder.write()
        #d_recorder.track_all(self._d_c_extractor)
        #d_recorder.write()


        return self.returned_data_creator('fin')

    def run_with_multi_scrs(self, app_id=0):
        self._logger.info("run: Init RPC client")
        remote_rpc_clis = [RpcClient(dst_addr=addr) for addr in self._m_opt['dst_addrs']]
        local_rpc_cli = RpcClient(dst_addr='127.0.0.1')
        dst_first_packet_ids =0
        src_last_packet_id =0
        dst_local_addrs = ["192.168.2.22", "192.168.3.33"] # NUC-2, NUC-3
        max_workers = len(dst_local_addrs)

        redis_cli = RedisClient()
        d_recorder = DiskRecorder('dcm_multi_{0}_{1}'.format(self._packet_rate, self._c_name))
        t_recorder = TimeRecorder('dcm_multi_{0}_{1}'.format(self._packet_rate, self._c_name), migration_type="dcm")
        r_recorder = ResourceRecorder('dcm_multi_{0}_{1}'.format(self._packet_rate, self._c_name))
        #for i in range(len(dst_local_addrs)):
        #    buf_loggers = BufferLogger('dcm_multi_{0}_{1}'.format(self._packet_rate, self._c_name),dst_addr=self._m_opt['dst_addrs'])

        r_recorder.insert_init_cond()
        r_recorder.track_on_subp()
        t_recorder.track(DataConsistencyMigrationConst.MIGRATION_TIME)

        #### src app info
        # Check docker_migration.proto for refering data format of app_info_dict
        t_recorder.track(DataConsistencyMigrationConst.SRC_GET_APP_INFO)
        app_info_dict = local_rpc_cli.get_app_info_dict(app_id)
        t_recorder.track(DataConsistencyMigrationConst.SRC_GET_APP_INFO)

        #### dst create buffer
        print('create buffer')
        t_recorder.track(DataConsistencyMigrationConst.DST_CREATE_BUF)
        dst_app_ids=[]
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="thread") as executor:
            futures = []
            for cli in remote_rpc_clis:
                futures.append(executor.submit(cli.prepare_app_launch, app_info_dict.buf_loc, app_info_dict.sig_loc,[str(e) for e in app_info_dict.rules]))
            dst_app_ids = [f.result() for f in futures]
        t_recorder.track(DataConsistencyMigrationConst.DST_CREATE_BUF)

        ### check src and dst buffer
        print('check whether first packet is arrived ad src node')
        t_recorder.track(DataConsistencyMigrationConst.SRC_CHECK_DST_PACKET_ARRAIVAL)
        dst_first_packet_ids=[]
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="thread") as executor:
            futures = []
            for i in range(len(remote_rpc_clis)):
                futures.append(executor.submit(remote_rpc_clis[i].get_buf_info, dst_app_ids[i], ClientBufInfo.BUF_FIRST.value, ScrDirection.C2S.value))  #in this case packet_id
            dst_first_packet_ids = [f.result() for f in futures]
        print(dst_first_packet_ids)
        for dst_first_packet_id in dst_first_packet_ids:
            if (not (local_rpc_cli.check_packet_arrival(app_id, dst_first_packet_id))):
                return self.returned_data_creator('create')
        t_recorder.track(DataConsistencyMigrationConst.SRC_CHECK_DST_PACKET_ARRAIVAL)


        # check whether last src packet is arrived at dst node
        print('check whether last src packet is arrived ad dst node')
        t_recorder.track(DataConsistencyMigrationConst.DST_CHECK_SRC_PACKET_ARRAIVAL)

        #rd = rdict(redis_cli.hgetall(app_id))
        #src_last_packet_ids = [ rd["{0}.*{1}".format(ScrDirection.S2C.value, addr)][0] for addr in dst_local_addrs]
        #print(rd)
        #print(src_last_packet_ids)

        dst_first_S2C_packet_ids=[]
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="thread") as executor:
            futures = []
            for i in range(len(remote_rpc_clis)):
                futures.append(executor.submit(remote_rpc_clis[i].get_buf_info, dst_app_ids[i], ClientBufInfo.BUF_FIRST.value, ScrDirection.S2C.value))  #in this case packet_id
            dst_first_S2C_packet_ids = [f.result() for f in futures]
        print(dst_first_S2C_packet_ids)
        for dst_first_packet_id in dst_first_S2C_packet_ids:
            if (not (local_rpc_cli.check_packet_arrival(app_id, dst_first_packet_id))):
                return self.returned_data_creator('create')
        t_recorder.track(DataConsistencyMigrationConst.DST_CHECK_SRC_PACKET_ARRAIVAL)

        ####  request ready for checkpoint
        # del buffer
        print('prepare for checkpoint')
        t_recorder.track(DataConsistencyMigrationConst.SRC_DEL_RULES_AND_BUF)
        local_rpc_cli.prepare_for_checkpoint(app_id)
        t_recorder.track(DataConsistencyMigrationConst.SRC_DEL_RULES_AND_BUF)

        # Inspect Images
        #code = remote_rpc_cli.inspect(i_name=self._i_name, version=self._version, c_name=self._c_name)

        # Check signal status
        print('check status')
        t_recorder.track(DataConsistencyMigrationConst.DST_CHECK_STATUS)
        is_ready = local_rpc_cli.check_status(app_id)
        if is_ready is False:
            return self.returned_data_creator('check_status', code=HTTPStatus.INTERNAL_SERVER_ERROR.value)
        t_recorder.track(DataConsistencyMigrationConst.DST_CHECK_STATUS)

        # Checkpoint
        print("==============checkpoint==============")
        t_recorder.track(DataConsistencyMigrationConst.CHECKPOINT)
        t_recorder.track(DataConsistencyMigrationConst.SERVICE_DOWNTIME)
        has_checkpointed = self._d_cli.checkpoint(self._c_name)
        t_recorder.track(DataConsistencyMigrationConst.CHECKPOINT)
        if has_checkpointed is not True:
            return self.returned_data_creator('checkpoint', code=HTTPStatus.INTERNAL_SERVER_ERROR.value)

        print("create tmp dir")
        has_created=[]
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="thread") as executor:
            futures = []
            for cli in remote_rpc_clis:
                futures.append(executor.submit(cli.create_tmp_dir, self._c_id))
            has_created = [f.result() for f in futures]
        #if all(has_created) is not CODE_SUCCESS:
        #    return self.returned_data_creator('checkpoint', code=HTTPStatus.INTERNAL_SERVER_ERROR.value)

        # Send artifacts
        print("rsync")
        t_recorder.track(DataConsistencyMigrationConst.RSYNC_C_FS)
        has_sent=[]
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="thread") as executor:
            futures = []
            for addr in (self._m_opt['dst_addrs']):
                futures.append(executor.submit(self._d_c_extractor.transfer_container_artifacts, addr))
            has_sent = [f.result() for f in futures]
        if all(has_sent) is not True:
            return self.returned_data_creator('send_checkpoint', code=HTTPStatus.INTERNAL_SERVER_ERROR.value)
        t_recorder.track(DataConsistencyMigrationConst.RSYNC_C_FS)

        print("allocate_fs")
        t_recorder.track(DataConsistencyMigrationConst.ALLOCATE_FS)
        volumes=[ volume.hash_converter() for volume in self._d_c_extractor.volumes]
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="thread") as executor:
            for i in range(len(remote_rpc_clis)):
                executor.submit(remote_rpc_clis[i].allocate_container_artifacts, self._d_c_extractor.c_name, self._d_c_extractor.c_id, self._d_c_extractor.i_layer_ids, self._d_c_extractor.c_layer_ids, volumes)
        t_recorder.track(DataConsistencyMigrationConst.ALLOCATE_FS)

        # Reload daemon
        print("reload")
        has_reload=[]
        t_recorder.track(DataConsistencyMigrationConst.RELOAD)
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="thread") as executor:
            futures = []
            for cli in remote_rpc_clis:
                futures.append(executor.submit(cli.reload_daemon))
            has_reload = [f.result() for f in futures]
        if has_reload != [CODE_SUCCESS, CODE_SUCCESS]:
            return self.returned_data_creator('send_checkpoint')
        t_recorder.track(DataConsistencyMigrationConst.RELOAD)

        # Update application buffer read offset
        print("update offset")
        rd = rdict(redis_cli.hgetall(app_id))
        t_recorder.track(DataConsistencyMigrationConst.DST_UPDATE_OFFSET)
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="thread") as executor:
            futures = []
            for i in range(len(remote_rpc_clis)):
                C2S_info = {"direction": ScrDirection.C2S.value, "packet_id": rd["{0}.*{1}".format(ScrDirection.C2S.value, dst_local_addrs[i])][0]}
                S2C_info = {"direction": ScrDirection.S2C.value, "packet_id": rd["{0}.*{1}".format(ScrDirection.S2C.value, dst_local_addrs[i])][0]}
                print(C2S_info)
                print(S2C_info)
                code = executor.submit(remote_rpc_clis[i].update_buf_read_offset, app_id, [C2S_info, S2C_info])
        t_recorder.track(DataConsistencyMigrationConst.DST_UPDATE_OFFSET)

        # Restore
        print("restore")
        codes= []
        t_recorder.track(DataConsistencyMigrationConst.RESTORE)
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="thread") as executor:
            futures = []
            for cli in remote_rpc_clis:
                futures.append(executor.submit(cli.restore, self._c_name))
            codes = [f.result() for f in futures]
        #if codes != [CODE_SUCCESS, CODE_SUCCESS]:
        #    return self.returned_data_creator("restore", code=code)

        t_recorder.track(DataConsistencyMigrationConst.RESTORE)
        t_recorder.track(DataConsistencyMigrationConst.SERVICE_DOWNTIME)
        t_recorder.track(DataConsistencyMigrationConst.MIGRATION_TIME)
        r_recorder.terminate_subp()

        # Write data
        t_recorder.write()
        r_recorder.write()
        d_recorder.track_all(self._d_c_extractor)
        d_recorder.write()


        print('check data consistency')
        #buf_logger.run()

        return self.returned_data_creator('fin')

    """
    Checkpoint and send checkpoint data to dst host

    @params String repo
    @params String tag
    @return True|False
    """
    def send_checkpoint(self, src_repo, tag):
        src_c = self._d_cli.container_presence(self._c_name)
        dst_dir_name = '{0}_{1}'.format(self._i_name.replace("/","_"),tag)
        cp_path = '{0}/{1}/'.format(self._d_config['checkpoint']['default_dir'], src_c.id)
        dst_path = '{0}/{1}/'.format(self._d_config['destination']['default_dir'], dst_dir_name)
        is_success = Rsync.call(cp_path, dst_path, 'miura', src_addr=None, dst_addr=self._m_opt['dst_addr'])
        return is_success

    def send_volume(self, dst_repo, tag, volumes):
        src_c = self._d_cli.container_presence(self._c_name)
        dir_name = '{0}_{1}'.format(self._i_name,tag)
        for vo in volumes:
            src_path = vo['h_path']
            dst_path = '{0}/{1}/'.format(self._d_config['destination']['default_dir'], dir_name)
            is_success = Rsync.call(src_path, dst_path, 'miura', src_addr=None, dst_addr=self._m_opt['dst_addr'])
            if is_success is False:
                return False
        return True

    """
    Create docker tag, which is unique to generated worker
    @params None
    @return String tag
    """
    def tag_creator(self):
        return datetime.now().strftime('%Y%m%d_%H%M%S')

    """
    Create message for explaning status to those who request with migration API

    @params String func_name
    @params Integer code
    @params dict        { "data": dict, "status": Integer }
            data        { "message": String, "container_dict": dict }
            container_dict   { "image_name": String, "version": String, "container_name": String }
    """
    def returned_data_creator(self, func_name, dst_app_id=0):
        container_dict = { "image_name": self._i_name, "version": self._version, "container": self._c_name, "dst_app_id": dst_app_id }
        data = { "container_dict": container_dict }

        if func_name is "ping":
            data["message"] = "dockerd is not running"
            return { "data": data, "status": HTTPStatus.INTERNAL_SERVER_ERROR.value }
        elif func_name is "restore":
            data["message"] = "cannot restore"
            return { "data": data, "status": HTTPStatus.INTERNAL_SERVER_ERROR.value }
        elif func_name is "migration_request":
            data["message"] = "cannot checkpoint"
            return { "data": data, "status": HTTPStatus.INTERNAL_SERVER_ERROR.value }
        elif func_name is 'create':
            data["message"] = "cannot create container"
            return { "data": data, "status": HTTPStatus.INTERNAL_SERVER_ERROR.value }
        elif func_name is 'checkpoint':
            data["message"] = "cannot checkpoint"
            return { "data": data, "status": HTTPStatus.INTERNAL_SERVER_ERROR.value }
        elif func_name is 'check_status':
            data["message"] = "cannot check status, check destination node is running"
            return { "data": data, "status": HTTPStatus.INTERNAL_SERVER_ERROR.value }
        elif func_name is 'volume':
            data["message"] = "cannot volume"
            return { "data": data, "status": HTTPStatus.INTERNAL_SERVER_ERROR.value }
        elif func_name is 'send_checkpoint':
            data["message"] = 'cannot send checkpoint data'
            return { "data": data, "status": HTTPStatus.BAD_REQUEST.value}
        elif func_name is  "commit":
            data["message"] = 'cannot commit the container '
            return { "data": data, "status": HTTPStatus.BAD_REQUEST.value}
        elif func_name is  "push":
            data["message"] = 'cannot push generated image'
            return { "data": data, "status": HTTPStatus.INTERNAL_SERVER_ERROR.value }
        elif func_name is 'fin':
            data["message"] = "Accepted"
            return { "data": data, "status": HTTPStatus.OK.value}
        else:
            data["message"] = "unknown function"
            return { "data": data, "status": HTTPStatus.BAD_REQUEST.value}

