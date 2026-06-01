# This Python file uses the following encoding: utf-8
# @brief    Orochi moans leader version (魂土司机：随时自由开车版)
# @author   jackyhwei
# @note     draft version without full test
# github    https://github.com/roarhill/oas

import random
from time import sleep
from datetime import time, datetime, timedelta
from enum import Enum
import numpy as np

from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Component.GeneralInvite.config_invite import FindMode, InviteConfig, InviteNumber
# from tasks.Component.GeneralInvite.general_invite import GeneralInvite, RoomType
from tasks.OrochiNew.orochi_invite import OrochiInvite, OrochiRoomType
from tasks.Component.GeneralBuff.general_buff import GeneralBuff
from tasks.Component.GeneralRoom.general_room import GeneralRoom
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
from tasks.GameUi.game_ui import GameUi
from tasks.GameUi.page import page_main, page_soul_zones, page_shikigami_records

from module.logger import logger
from module.exception import TaskEnd
from module.base.timer import Timer

from tasks.OrochiNew.assets import OrochiNewAssets
from tasks.OrochiNew.config import OrochiNew, UserStatus

from tasks.Dokan.assets import DokanAssets
from tasks.Orochi.assets import OrochiAssets

class OrochiNewScene(Enum):
    '''
    FIXME 这些状态里，需要一个优先顺序
    '''
    # 未知界面（随机点击3次，以便跳过一些不支持的结算界面）
    OROCHI_SCENE_UNKNOWN = 0
    # 场景检测：组队界面（需要自己预先拉好一个队友）
    OROCHI_SCENE_TEAM = 1
    # 场景检测：进入御魂战斗，但未点开始
    OROCHI_SCENE_IN_FIELD = 2
    # 场景检测：御魂战斗进行中
    OROCHI_SCENE_FIGHTING = 3

class ScriptTask(GeneralBattle, OrochiInvite, GeneralBuff, GeneralRoom, GameUi, SwitchSoul, OrochiNewAssets):
    in_orochi: bool = False
    current_scene: OrochiNewScene = OrochiNewScene.OROCHI_SCENE_UNKNOWN
    anti_detect_click_fixed_random_area: bool = True
    my_config: OrochiNew = None

    # 限制时间 
    limit_time: timedelta
    # 限制次数 
    limit_count: int = 30
    current_count: int = 0
    # 限制突破券
    limit_toppa_scrolls_enabled: bool = False
    limit_toppa_scrolls_count: int = 30
    current_toppa_scroll_count: int = 0
    # 只在第一次的时候会去点一下查看一下当前拥有的突破券数量
    is_first_check_toppa_scrolls: bool = True
    # 房间类型
    orochi_room_type: OrochiRoomType = OrochiRoomType.NORMAL_3

    def run(self) -> bool:
        '''
        御魂主函数
        '''
        self.my_config: OrochiNew = self.config.orochi_new
        if self.my_config is None:
            logger.error('my_config is None')
            return False

        self.limit_time = self.my_config.orochi_new_config.limit_time
        self.limit_count = self.my_config.orochi_new_config.limit_count
        self.limit_time = timedelta(hours=self.limit_time.hour, minutes=self.limit_time.minute, seconds=self.limit_time.second)
        # self.limit_toppa_scrolls_enabled = self.my_config.orochi_new_config.limit_by_toppa_scrolls_enable
        # self.limit_toppa_scrolls_count = self.my_config.orochi_new_config.limit_by_toppa_scrolls_count
        self.orochi_room_type: OrochiRoomType = OrochiRoomType.NORMAL_3

        print(f"config={self.my_config}")

        # 检测当前界面的场景（仅支持：组队界面、准备界面和战斗界面）, 如果检测到不能识别的场景，先随便点击三下，再次检测
        detect_count = 0
        while not self.in_orochi:
            self.in_orochi, self.current_scene = self.orochi_get_scene(False)
            logger.warning(f"try {detect_count}/3: self.in_orochi={self.in_orochi}, self.current_scene={self.current_scene}")
            sleep(1)
            detect_count += 1
            if detect_count >= 3:
                break

        # 如果不在可支持的场景界面，按正常的流程走
        if not self.in_orochi:
            self.orochi_switch_soul(self.my_config)
            self.orochi_open_soul_buf(self.my_config)

        # 开始战斗
        success = True
        match self.my_config.orochi_new_config.user_status:
            case UserStatus.LEADER: success = self.orochi_run_leader(self.current_scene)
            case UserStatus.MEMBER: success = self.orochi_run_member(self.current_scene)
            case _: logger.error('current version supports only running leader mode!')

        # 无论是否启用加成，都检查一下，并关一下
        self.open_buff()
        self.soul(is_open=False)
        self.close_buff()

        # 下一次运行时间
        if success:
            self.set_next_run('OrochiNew', finish=True, success=True)
        else:
            self.set_next_run('OrochiNew', finish=False, success=False)

        raise TaskEnd

    def orochi_open_soul_buf(self, config: OrochiNew):
        '''
        在庭院界面打开御魂加成（考虑放到组队成功、点击挑战前）
        '''
        self.ui_get_current_page()
        self.ui_goto(page_main)
        if config.orochi_new_config.soul_buff_enable:
            self.open_buff()
            self.soul(is_open=True)
            self.close_buff()

    def orochi_switch_soul(self, config: OrochiNew):
        '''
        切换御魂
        '''
        # 御魂切换方式一
        if config.switch_soul.enable:
            self.ui_get_current_page()
            self.ui_goto(page_shikigami_records)
            self.run_switch_soul(config.switch_soul.switch_group_team)

        # 御魂切换方式二
        if config.switch_soul.enable_switch_by_name:
            self.ui_get_current_page()
            self.ui_goto(page_shikigami_records)
            self.run_switch_soul_by_name(config.switch_soul.group_name,
                                         config.switch_soul.team_name)


    def orochi_enter(self) -> bool:
        logger.info('Enter orochi')
        while True:
            self.screenshot()
            if self.appear(OrochiAssets.I_FORM_TEAM):
                return True
            if self.appear_then_click(OrochiAssets.I_OROCHI, interval=1):
                continue

    def orochi_check_layer(self, layer: str) -> bool:
        """
        检查挑战的层数, 并选中挑战的层
        :return:
        """
        pos = self.list_find(self.L_LAYER_LIST_NEW, layer)
        if pos:
            self.device.click(x=pos[0], y=pos[1])
            return True

    def orochi_is_in_prepare(self, is_screenshot: bool = True) -> bool:
        """
        判断是否在准备中
        :return:
        """
        if is_screenshot:
            self.screenshot()
        if self.appear(self.I_OROCHI_PREPARE):
            return True
        if self.appear(self.I_BUFF):
            return True
        elif self.appear(self.I_PREPARE_HIGHLIGHT):
            return True
        elif self.appear(self.I_PREPARE_DARK):
            return True
        elif self.appear(self.I_PRESET) or self.appear(self.I_PRESET_WIT_NUMBER):
            return True
        else:
            return False

    def orochi_get_scene(self, reuse_screenshot: bool = True):
        '''
        识别御魂任务场景
        '''
        if not reuse_screenshot:
            self.screenshot()
        
        # 场景检测：组队界面（需要自己预先拉好队友）
        if self.is_in_prepare():
            return True, OrochiNewScene.OROCHI_SCENE_IN_FIELD
        if self.is_in_battle():
            return True, OrochiNewScene.OROCHI_SCENE_FIGHTING

        # 两人队伍，并且已经拉好一个队友
        if not self.appear(self.I_ADD_1) and self.appear(self.I_ADD_2) and self.appear(self.I_FIRE):
            return True, OrochiNewScene.OROCHI_SCENE_TEAM

        # 三人队伍，并且已经组好队
        if not self.appear(self.I_ADD_1) and not self.appear(self.I_ADD_2) and self.appear(self.I_FIRE):
            return True, OrochiNewScene.OROCHI_SCENE_TEAM

        if self.orochi_is_in_prepare():
            return True, OrochiNewScene.OROCHI_SCENE_TEAM

        # 战斗胜利，结算
        # if self.appear_then_click(self.I_OROCHI_SUCCEED):

        # 点击一个安全区域跳过各种乱七八糟的结算界面，比如：皮肤碎片
        if self.appear(self.I_OROCHI_SUCCEED2) or self.appear(self.I_OROCHI_SUCCEED):
            self.click(DokanAssets.C_DOKAN_RANDOM_CLICK_AREA2)
            return True, OrochiNewScene.OROCHI_SCENE_FIGHTING
        
        return False, OrochiNewScene.OROCHI_SCENE_UNKNOWN

    def orochi_run_leader(self, scene: OrochiNewScene = OrochiNewScene.OROCHI_SCENE_UNKNOWN):
        '''
        御魂司机流程（原run_leader函数存在问题，又不想改原函数，怕影响现有的其他功能，因此独立出来实现）
        '''
        logger.info(f'Start run leader:scene={scene}')

        manual_start = False
        is_first = True

        # 未知界面启动，走正常流程
        if scene == OrochiNewScene.OROCHI_SCENE_UNKNOWN:
            self.ui_get_current_page()
            self.ui_goto(page_soul_zones)
            self.orochi_enter()
            # 创建队伍
            logger.info('Create team')
            while 1:
                self.screenshot()
                if self.appear_then_click(OrochiAssets.I_FORM_TEAM, interval=1):
                    logger.info("111 form team")
                    break

            layer = self.my_config.orochi_new_config.layer
            logger.info(f"finding Orochi layer: {layer}")
            self.orochi_check_layer(layer)

            # 创建房间
            self.create_room()
            self.ensure_private()
            self.create_ensure()
        # elif scene == OrochiNewScene.OROCHI_SCENE_TEAM:
        #     is_first = False
        #     manual_start = True
        else:
            is_first = False
            manual_start = True

        success = True

        # 这个时候我已经进入房间了哦
        while 1:
            logger.warning(f"manual_start={manual_start}, first={is_first}, {self.current_count}/{self.limit_count}")
            self.screenshot()

            # 检查猫咪奖励
            if self.appear_then_click(OrochiAssets.I_PET_PRESENT, action=self.C_WIN_3, interval=1):
                continue

            if manual_start and not is_first:
                if self.orochi_check_and_skip_battle_result() == True:
                    self.check_and_invite(self.my_config.invite_config.default_invite)
                    continue

            # 无论胜利与否, 都会出现是否邀请一次队友
            # 区别在于，失败的话不会出现那个勾选默认邀请的框
            if self.check_and_invite(self.my_config.invite_config.default_invite):
                continue

            # 次数达到上限
            if self.current_count >= self.limit_count:
                if self.is_in_room():
                    logger.info('Orochi count limit out')
                    break
            # 时间达到上限
            if datetime.now() - self.start_time >= self.limit_time:
                if self.is_in_room():
                    logger.info('Orochi time limit out')
                    break
            # 突破券达到上限
            if self.limit_toppa_scrolls_enabled and self.current_toppa_scroll_count >= self.limit_toppa_scrolls_count:
                if self.is_in_room():
                    logger.info('Toppa scrolls limit out: current={self.current_toppa_scrolls_count}/{self.limit_toppa_scrolls_limit}')
                    break

            # 如果没有进入房间那就不需要后面的邀请
            if not self.is_in_room():
                if self.orochi_is_room_dead():
                    logger.warning('Orochi task failed')
                    success = False
                    break
                continue

            # 点击挑战
            if not is_first:
                if self.orochi_run_invite(config=self.my_config.invite_config, is_first=False):
                    self.run_general_battle(config=self.my_config.general_battle_config)
                else:
                    # 邀请失败，退出任务
                    logger.warning('Invite failed and exit this orochi task')
                    success = False
                    break
            else:
                if manual_start:
                    is_first = False
                    self.run_general_battle(config=self.my_config.general_battle_config)
                else:
                    if not self.orochi_run_invite(config=self.my_config.invite_config, is_first=True):
                        logger.warning('Invite failed and exit this orochi task')
                        success = False
                        break
                    else:
                        is_first = False
                        self.run_general_battle(config=self.my_config.general_battle_config)

        # 当结束或者是失败退出循环的时候只有两个UI的可能，在房间或者是在组队界面
        # 如果在房间就退出
        if self.exit_room():
            pass
        # 如果在组队界面就退出
        if self.exit_team():
            pass

        self.ui_get_current_page()
        self.ui_goto(page_main)

        return success

    def orochi_run_member(self, scene: OrochiNewScene = OrochiNewScene.OROCHI_SCENE_UNKNOWN):
        '''
        御魂队员流程（原run_member函数存在问题，又不想改原函数，怕影响现有的其他功能，因此独立出来实现）
        '''
        logger.info('Start run member')
        self.ui_get_current_page()

        # 进入战斗流程
        self.device.stuck_record_add('BATTLE_STATUS_S')
        while 1:
            self.screenshot()

            # 检查猫咪奖励
            if self.appear_then_click(OrochiAssets.I_PET_PRESENT, action=self.C_WIN_3, interval=1):
                continue
            # 次数达到上限
            if self.current_count >= self.limit_count:
                logger.info('Orochi count limit out')
                break
            # 时间达到上限
            if datetime.now() - self.start_time >= self.limit_time:
                logger.info('Orochi time limit out')
                break
            # 突破券达到上限
            if self.limit_toppa_scrolls_enabled and self.current_toppa_scroll_count >= self.limit_toppa_scrolls_count:
                logger.info('Orochi task terminated due to toppa scrolls limit: current={self.current_toppa_scrolls_count}/{self.limit_toppa_scrolls_limit}')
                break

            if self.check_then_accept():
                continue

            if self.is_in_room():
                self.device.stuck_record_clear()
                if self.wait_battle(wait_time=self.my_config.invite_config.wait_time):
                    self.run_general_battle(config=self.my_config.general_battle_config)
                else:
                    break
            # 队长秒开的时候，检测是否进入到战斗中
            elif self.check_take_over_battle(False, config=self.my_config.general_battle_config):
                continue

        while 1:
            # 有一种情况是本来要退出的，但是队长邀请了进入的战斗的加载界面
            if self.appear(self.I_GI_HOME) or self.appear(self.I_GI_EXPLORE):
                break
            # 如果可能在房间就退出
            if self.exit_room():
                pass
            # 如果还在战斗中，就退出战斗
            if self.exit_battle():
                pass

        self.ui_get_current_page()
        self.ui_goto(page_main)

        return True

    def orochi_is_room_dead(self) -> bool:
        '''
        如果在探索界面或者是出现在组队界面，那就是可能房间死了
        '''
        sleep(0.5)
        if self.appear(self.I_MATCHING) or self.appear(self.I_CHECK_EXPLORATION):
            sleep(0.5)
            if self.appear(self.I_MATCHING) or self.appear(self.I_CHECK_EXPLORATION):
                return True
        return False
    
    def orochi_check_and_skip_battle_result(self, reuse_screenshot: bool = True) -> bool:
        '''
        检查是否当前为各种战斗结算界面之一，如果是，点击以便跳过该界面。
        TODO 部分界面有顺序关系，考虑按顺序实现点击以避免不必要的匹配。
        '''
        if not reuse_screenshot:
            self.screenshot()

        # 打完后，第一个界面，左上角有一个统计，但是这个图不对，先跳过（跳过的结果是：会等界面超时自动跳转到：第二个界面，左下角有一个统计）
        if self.appear(self.I_STATISTICS, threshold=0.8):
            logger.info("OrochiNew was started at {self.I_STATISTICS.name}")
            # self.ui_click_until_disappear(self.I_STATISTICS, interval=0.5)
            self.click(click=DokanAssets.C_DOKAN_RANDOM_CLICK_AREA2, interval=0.5)
            return True

        # 打完后，第二个界面，左下角有一个统计
        if self.appear(self.I_REWARD_STATISTICS, threshold=0.8):
            logger.info("OrochiNew was started at {self.I_REWARD_STATISTICS.name}")
            self.click(click=DokanAssets.C_DOKAN_RANDOM_CLICK_AREA2, interval=0.5)
            return True

        # 打完后，第三个界面，挑战成功
        if self.appear(self.I_WIN):
            action_click = random.choice([self.C_WIN_1, self.C_WIN_2, self.C_WIN_3])
            self.click(click=action_click, interval=0.8)
            return True

        # 出现失败 就点击
        if self.appear_then_click(self.I_FALSE, threshold=0.8):
            logger.info("OrochiNew was started at {self.I_FALSE.name}")
            return True

        # 领奖励
        if self.appear(self.I_REWARD, threshold=0.65):
            # action_click = random.choice([self.C_REWARD_1, self.C_REWARD_2, self.C_REWARD_3])
            # self.click(click=action_click, interval=1.2)
            self.click(click=DokanAssets.C_DOKAN_RANDOM_CLICK_AREA2, interval=0.5)
            logger.info("OrochiNew was started at {self.I_REWARD.name}")
            return True

        # 领奖励出现金币
        if self.appear_then_click(self.I_REWARD_GOLD, threshold=0.8):
            logger.info("OrochiNew was started at {self.I_REWARD_GOLD.name}")
            return True

        # 猫咪奖励
        if self.appear(OrochiAssets.I_PET_PRESENT):
            action_click = random.choice([self.C_WIN_1, self.C_WIN_2, self.C_WIN_3])
            self.click(click=action_click, interval=0.6)
            return True

        return False
    
    def orochi_check_toppa_scroll(self, reuse_screenshot: bool = True) -> bool:
        '''
        检查突破券掉落
        '''
        if not reuse_screenshot:
            self.screenshot()

        # 匹配突破券
        if self.I_TOPPA_SCROLL.match(self.device.image):
            if self.is_first_check_toppa_scrolls:
                # 仅第一次发现突破券的时候去点击，以查看当前突破券数量
                self.click(self.I_TOPPA_SCROLL)
                self.screenshot()
                cu, res, total = self.O_TOPPA_SCROLL.ocr(self.device.image)
                logger.warning(f'toppa scroll, cu={cu}, res={res}, total={total}')
                if cu == 0 and cu + res == total:
                    self.current_toppa_scroll_count = cu
                self.is_first_check_toppa_scrolls = False
            else:
                self.current_toppa_scroll_count += 1
            return True

        return False

    def battle_wait(self, random_click_swipt_enable: bool) -> bool:
        """
        战斗等待，加入突破券统计
        :param random_click_swipt_enable: 
        :return: True 战斗成功, False 战斗失败
        """
        # 重写
        self.device.stuck_record_add('BATTLE_STATUS_S')
        self.device.click_record_clear()
        self.C_REWARD_1.name = 'C_REWARD'
        self.C_REWARD_2.name = 'C_REWARD'
        self.C_REWARD_3.name = 'C_REWARD'

        # 战斗过程 随机点击和滑动 防封
        # logger.info("OrochiNew orochi_battle_wait")

        while 1:
            self.screenshot()
            action_click = random.choice([self.C_WIN_1, self.C_WIN_2, self.C_WIN_3])
            if self.appear_then_click(self.I_WIN, action=action_click ,interval=0.8):
                # 赢的那个鼓
                continue
            if self.appear(self.I_GREED_GHOST):
                # 检查突破券
                self.orochi_check_toppa_scroll()

                # 贪吃鬼
                logger.info('OrochiNew orochi_battle_wait:Win battle')
                self.wait_until_appear(self.I_REWARD, wait_time=1.5)
                self.screenshot()
                if not self.appear(self.I_GREED_GHOST):
                    logger.warning('OrochiNew orochi_battle_wait: Greedy ghost disappear. Maybe it is a false battle')
                    continue
                while 1:
                    self.screenshot()
                    action_click = random.choice([self.C_REWARD_1, self.C_REWARD_2, self.C_REWARD_3])
                    if not self.appear(self.I_GREED_GHOST):
                        break
                    if self.click(action_click, interval=1.5):
                        continue
                return True
            if self.appear(self.I_REWARD):
                # 魂
                logger.info('OrochiNew orochi_battle_wait: Win battle')
                # appear_greed_ghost = self.appear(self.I_GREED_GHOST)
                while 1:
                    self.screenshot()
                    action_click = random.choice([self.C_REWARD_1, self.C_REWARD_2, self.C_REWARD_3])
                    if self.appear_then_click(self.I_REWARD, action=action_click, interval=1.5):
                        continue
                    if not self.appear(self.I_REWARD):
                        break
                return True

            if self.appear(self.I_FALSE):
                logger.warning('OrochiNew orochi_battle_wait: False battle')
                self.ui_click_until_disappear(self.I_FALSE)
                return False

            # 如果开启战斗过程随机滑动
            if random_click_swipt_enable:
                self.random_click_swipt()

    def orochi_run_invite(self, config: InviteConfig, is_first: bool = False) -> bool:
        """
        队长！！身份。。。在组队界面邀请好友（ 如果开启is_first） 等待队员进入开启挑战
        请注意，返回的时候成功时是进入战斗了！！！
        如果是失败，那就是没有队友进入，然后会退出房间的界面
        :param config:
        :param is_first: 如果是第一次开房间的那就要邀请队员，其他情况等待队员进入
        :return:
        """
        logger.hr('[] Orochi invite friend', 2)
        if not self.ensure_enter():
            logger.warning('[] Not enter invite page')
            return False
        if is_first:
            _ = self.orochi_room_type
            self.timer_invite = Timer(20)
            self.timer_invite.start()
            logger.info(f"config.invite_number={config.invite_number}")
            self.orochi_ensure_room_type(config.invite_number)
            self.orochi_invite_friends(config)
        else:
            self.timer_invite = Timer(30)
            self.timer_invite.start()
            self.timer_emoji = Timer(20)
            self.timer_emoji.start()
        wait_second = config.wait_time.second + config.wait_time.minute * 60
        self.timer_wait = Timer(wait_second)
        self.timer_wait.start()
        while 1:
            self.screenshot()
            if self.timer_wait.reached():
                logger.warning('[] Wait timeout')
                return False
            if self.appear(self.I_MATCHING):
                logger.warning('[] Timeout, now is no room')
                return False

            if not self.is_in_room():
                continue

            if self.timer_emoji and self.timer_emoji.reached():
                self.timer_emoji.reset()
                self.appear_then_click(self.I_GI_EMOJI_1)
                self.appear_then_click(self.I_GI_EMOJI_2)

            fire = False  # 是否开启挑战

            appear_add_1 = self.appear(self.I_ADD_1)
            appear_add_2 = self.appear(self.I_ADD_2)
            logger.info(
                f"[] appear_add_1={appear_add_1}, appear_add_2={appear_add_2}, config.invite_number={config.invite_number}, self.orochi_room_type={self.orochi_room_type}, OrochiRoomType.NORMAL_2={OrochiRoomType.NORMAL_2}"
            )
            # 如果这个房间最多只容纳两个人（意思是只可以邀请一个人），且已经邀请一个人了，那就开启挑战
            if self.orochi_room_type == OrochiRoomType.NORMAL_2 and not appear_add_1:
                logger.info('[] Start challenge and this room can only invite one friend')
                fire = True
            # 如果这个房间最多容纳三个人（意思是可以邀请两个人），且设定邀请一个就开启挑战，那就开启挑战
            elif self.orochi_room_type == OrochiRoomType.NORMAL_3 and config.invite_number == InviteNumber.ONE and not appear_add_1:
                logger.info('[] Start challenge and user only invite one friend')
                fire = True
            # 如果这个房间最多容纳三个人（意思是可以邀请两个人），且设定邀请两个就开启挑战，那就开启挑战
            elif self.orochi_room_type == OrochiRoomType.NORMAL_3 \
                    and config.invite_number == InviteNumber.TWO and not self.appear(self.I_ADD_2):
                logger.info('[] Start challenge and user invite two friends')
                fire = True
            # 如果这个房间是五人的，且设定邀请一个就开启挑战，那就开启挑战
            elif self.orochi_room_type == OrochiRoomType.NORMAL_5 \
                    and config.invite_number == InviteNumber.ONE and not self.appear(self.I_ADD_5_1):
                logger.info('[] Start challenge and user only invite one friend')
                fire = True
            # 如果这个房间是五人的，且设定邀请两个就开启挑战，那就开启挑战
            elif self.orochi_room_type == OrochiRoomType.NORMAL_5 \
                    and config.invite_number == InviteNumber.TWO and not self.appear(self.I_ADD_5_2):
                logger.info('[] Start challenge and user invite two friends')
                fire = True
            # 如果是永生之海
            elif self.orochi_room_type == OrochiRoomType.ETERNITY_SEA and not self.appear(self.I_ADD_SEA):
                logger.info('[] Start challenge and this is lock sea')
                fire = True

            # 点击挑战
            if fire:
                self.orochi_click_fire()
                return True

            if self.timer_invite and self.timer_invite.reached():
                if is_first:
                    logger.info('[] Invitation is triggered every 20s')
                    self.timer_invite.reset()
                else:
                    logger.info('[] Wait for 30s and invite again')
                    self.timer_invite = None
                self.orochi_invite_friends(config)

    def orochi_click_fire(self):
        while 1:
            self.screenshot()
            if not self.is_in_room(False):
                break
            if self.appear_then_click(self.I_OROCHI_FIRE, interval=1, threshold=0.7):
                continue
            if self.appear_then_click(self.I_FIRE, interval=1, threshold=0.7):
                continue
            if self.appear_then_click(self.I_FIRE_SEA, interval=1, threshold=0.7):
                continue

    def orochi_room_type(self) -> OrochiRoomType:
        """
        只需要在队长进入的时候判断一次就可以了，任务后面之间使用
        :return:
        """
        self.screenshot()
        orochi_room_type = self.orochi_check_room_type(image=self.device.image, pre_type=OrochiRoomType.NORMAL_3)
        logger.info(f'[] Orochi room type: {OrochiRoomType}')
        return orochi_room_type

    def orochi_check_room_type(self, image: np.array = None, pre_type: OrochiRoomType = None) -> OrochiRoomType:
        """
        检查房间类型：在加入自动、手动档结合的逻辑后，需要改变一个3和2的顺序，如果3个坑的队伍如果已经拉了1个人的话，原逻辑会被判定为2个坑的队伍
        :param image:
        :param pre_type: 可以先指定这个类型，如果不指定，就自动检查
        :return:
        """
        def check_3(img) -> bool:
            appear = False
            # if self.I_ADD_1.match(img) and self.I_ADD_2.match(img):
            # FIXME 三个人的房间，位置1已经有人了，按这个逻辑会变成两个人的房间
            # if self.I_ADD_1.match(img) and self.I_ADD_2.match(img):
            logger.warning(f"[] orochi_check_room_type, room3: {self.I_ADD_2.name}")
            if self.appear(self.I_ADD_2):
                appear = True
            return appear

        def check_2(img) -> bool:
            appear = False
            if not self.I_ADD_1.match(img) and self.I_ADD_2.match(img):
                appear = True
            return appear

        def check_5(img) -> bool:
            appear = False
            if self.I_ADD_5_1.match(img) and self.I_ADD_5_2.match(img) \
                    and self.I_ADD_5_3.match(img) and self.I_ADD_5_4.match(img):
                appear = True
            return appear

        def check_eternity_sea(img) -> bool:
            appear = False
            if self.I_LOCK_SEA.match(img) or self.I_UNLOCK_SEA.match(img):
                appear = True
            return appear

        orochi_room_type = None

        logger.debug(f"pre_type={pre_type}, check_2(image)={check_2(image)}, check_3(image)={check_2(image)}")

        if pre_type is not None:
            match pre_type:
                case OrochiRoomType.NORMAL_2:
                    orochi_room_type = OrochiRoomType.NORMAL_2 if check_2(image) else None
                case OrochiRoomType.NORMAL_3:
                    orochi_room_type = OrochiRoomType.NORMAL_3 if check_3(image) else None
                case OrochiRoomType.NORMAL_5:
                    orochi_room_type = OrochiRoomType.NORMAL_5 if check_5(image) else None
                case OrochiRoomType.ETERNITY_SEA:
                    orochi_room_type = OrochiRoomType.ETERNITY_SEA if check_eternity_sea(image) else None
        if orochi_room_type:
            return orochi_room_type

        logger.debug(f"orochi_room_type={orochi_room_type}")

        # FIXME 在加入自动、手动档结合的逻辑后，需要改变一个3和2的顺序，如果3个坑的队伍如果已经拉了1个人的话，原逻辑会被判定为2个坑的队伍
        if orochi_room_type is None and check_3(image):
            orochi_room_type = OrochiRoomType.NORMAL_3
            return orochi_room_type
        if orochi_room_type is None and check_2(image):
            orochi_room_type = OrochiRoomType.NORMAL_2
            return orochi_room_type


        if orochi_room_type is None and check_5(image):
            orochi_room_type = OrochiRoomType.NORMAL_5
            return orochi_room_type
        if orochi_room_type is None and check_eternity_sea(image):
            orochi_room_type = OrochiRoomType.ETERNITY_SEA
            return orochi_room_type
        return orochi_room_type

    def orochi_ensure_room_type(self, friend_number: int = None) -> bool:
        """
        确认设定的邀请人数是否会超出房间的最大
        :param friend_number: 这个输入的是用户选项中的invite_number
        :return:  如果超出了，就返回False
        """
        if isinstance(friend_number, InviteNumber):
            if friend_number == InviteNumber.ONE:
                friend_number = 1
            elif friend_number == InviteNumber.TWO:
                friend_number = 2

        if friend_number == 2:
            if self.orochi_room_type == OrochiRoomType.NORMAL_2:
                # 整个房间就可以两个人，还邀请两个 这个是报错的
                logger.error('[] Room can only be one people, but invite two people')
                return False
            elif self.orochi_room_type == OrochiRoomType.ETERNITY_SEA:
                # 永生之海，只能邀请一个人
                logger.error('[] Room can only be one people, but invite two people')
                return False
            return True
        return True

    def orochi_invite_friend(self, name: str = None, find_mode: FindMode = FindMode.AUTO_FIND) -> bool:
        """
        邀请好友
        :param find_mode: 寻找的方式
        :param name:
        :return:
        """
        logger.info('[] Click add to invite friend')
        # 点击＋号
        while 1:
            self.screenshot()
            if self.appear(self.I_LOAD_FRIEND):
                break
            if self.appear(self.I_INVITE_ENSURE):
                break
            if self.appear_then_click(self.I_ADD_2, interval=1):
                continue
            if self.appear_then_click(self.I_ADD_5_4, interval=1):
                continue
            if self.appear_then_click(self.I_ADD_SEA, interval=1):
                continue

        friend_class = []
        class_ocr = [self.O_F_LIST_1, self.O_F_LIST_2, self.O_F_LIST_3, self.O_F_LIST_4]
        class_index = 0
        list_1 = self.O_F_LIST_1.ocr(self.device.image)
        list_2 = self.O_F_LIST_2.ocr(self.device.image)
        list_3 = self.O_F_LIST_3.ocr(self.device.image)
        list_4 = self.O_F_LIST_4.ocr(self.device.image)
        list_1 = list_1.replace(' ', '').replace('、', '')
        list_2 = list_2.replace(' ', '').replace('、', '')
        list_3 = list_3.replace(' ', '').replace('、', '')
        if list_1 is not None and list_1 != '' and list_1 in self.friend_class:
            friend_class.append(list_1)
        if list_2 is not None and list_2 != '' and list_2 in self.friend_class:
            friend_class.append(list_2)
        if list_3 is not None and list_3 != '' and list_3 in self.friend_class:
            friend_class.append(list_3)
        if list_4 is not None and list_4 != '' and list_4 in self.friend_class:
            friend_class.append(list_4)
        for i in range(len(friend_class)):
            if friend_class[i] == '蔡友':
                friend_class[i] = '寮友'
            elif friend_class[i] == '路区':
                friend_class[i] = '跨区'
            elif friend_class[i] == '察友':
                friend_class[i] = '寮友'
            elif friend_class[i] == '区':
                friend_class[i] = '跨区'
        logger.info(f'[] Friend class: {friend_class}')

        is_select: bool = False  # 是否选中了好友
        if find_mode == FindMode.RECENT_FRIEND:
            logger.info('[] Find recent friend')
            # 获取’最近‘在friend_class中的index
            if '最近' not in friend_class:
                logger.warning('[] No recent friend')
                return False
            recent_index = friend_class.index('最近')
            while recent_index == 1:
                self.screenshot()
                if self.appear(self.I_FLAG_2_ON):
                    break
                if self.appear_then_click(self.I_FLAG_2_OFF, interval=1):
                    continue

            logger.info(f'[] Now find friend in ”最近“')
            sleep(1)
            if not is_select:
                if self.detect_select(name):
                    is_select = True
            sleep(1)
            if not is_select:
                if self.detect_select(name):
                    is_select = True

        for index in range(len(friend_class)):
            # 如果不是自动寻找，就跳过
            if find_mode != FindMode.AUTO_FIND:
                continue
            # 如果已经选中了好友，就不需要再选中了
            if is_select:
                continue
            # 首先切换到不同的好友列表
            while index == 0:
                self.screenshot()
                if self.appear(self.I_FLAG_1_ON):
                    break
                if self.appear_then_click(self.I_FLAG_1_OFF, interval=1):
                    continue
            while index == 1:
                self.screenshot()
                if self.appear(self.I_FLAG_2_ON):
                    break
                if self.appear_then_click(self.I_FLAG_2_OFF, interval=1):
                    continue
            while index == 2:
                self.screenshot()
                if self.appear(self.I_FLAG_3_ON):
                    break
                if self.appear_then_click(self.I_FLAG_3_OFF, interval=1):
                    continue
            while index == 3:
                self.screenshot()
                if self.appear(self.I_FLAG_4_ON):
                    break
                if self.appear_then_click(self.I_FLAG_4_OFF, interval=1):
                    continue

            # 选中好友， 在这里游戏获取在线的好友并不是很快，根据不同的设备会有不同的时间，而且没有什么元素提供我们来判断
            # 所以这里就直接等待一段时间
            logger.info(f'[] Now find friend in {friend_class[index]}')
            sleep(1)
            if not is_select:
                if self.detect_select(name):
                    is_select = True
            sleep(1)
            if not is_select:
                if self.detect_select(name):
                    is_select = True

        # 点击确定
        logger.info('[] Click invite ensure')
        if not self.appear(self.I_INVITE_ENSURE):
            logger.warning('No appear invite ensure while invite friend')
        while 1:
            self.screenshot()
            if not self.appear(self.I_INVITE_ENSURE):
                break
            if self.appear_then_click(self.I_INVITE_ENSURE):
                continue
        # 哪怕没有找到好友也有点击 确认 以退出好友列表
        if not is_select:
            logger.warning('No find friend')
            # 这个时候任务运行失败
            logger.info('Task failed')
            return False

        return True

    def orochi_invite_friends(self, config: InviteConfig) -> bool:
        """
        看情况邀请两个好友
        :return:
        """
        success = self.orochi_invite_friend(config.friend_1, config.find_mode)
        if not success:
            logger.warning('Invite friend 1 failed')
        # 如果是邀请第二个人
        if config.invite_number == InviteNumber.TWO:
            success = self.orochi_invite_friend(config.friend_2, config.find_mode)
            if not success:
                logger.warning('Invite friend 2 failed')
        sleep(0.5)


if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device
    c = Config('oas1')
    d = Device(c)
    t = ScriptTask(c, d)

    t.run()
