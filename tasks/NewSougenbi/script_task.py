# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from time import sleep
from datetime import time, datetime, timedelta

from tasks.NewSougenbi.assets import NewSougenbiAssets
from tasks.NewSougenbi.config import NewSougenbiConfig, NewSougenbiClass
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
from tasks.GameUi.game_ui import GameUi
from tasks.GameUi.page import page_main, page_soul_zones, page_shikigami_records
from module.logger import logger
from module.exception import TaskEnd

from tasks.NewSougenbi.scene import NewSougenbiSceneDetector, NewSougenbiScene

# class ScriptTask(ExtendGreenMark, GameUi, SwitchSoul, NewSougenbiSceneDetector):
# class ScriptTask(GeneralBattle, GameUi, SwitchSoul, NewSougenbiAssets, NewSougenbiSceneDetector):
class ScriptTask(GeneralBattle, GameUi, SwitchSoul, NewSougenbiSceneDetector):

    # def __init__(self, config: NewSougenbi, device: Device):
    #     super().__init__(config, device)


    def run(self):
        con = self.config.new_sougenbi
        if not con:
            raise TaskEnd('NewSougenbi config is None')
        if not con.new_sougenbi_config:
            raise TaskEnd('NewSougenbi config is None')

        s_con: NewSougenbiConfig = con.new_sougenbi_config
        limit_time = con.new_sougenbi_config.limit_time
        self.limit_time: timedelta = timedelta(hours=limit_time.hour, minutes=limit_time.minute,
                                               seconds=limit_time.second)
        self.in_sougenbi = False

        # 检测当前界面的场景（仅支持：组队界面、准备界面和战斗界面）, 如果检测到不能识别的场景，先随便点击三下，再次检测
        detect_count = 0
        while not self.in_sougenbi:
            self.in_sougenbi, self.current_scene = self.get_current_scene(False)
            logger.warning(f"try {detect_count}/3: self.in_sougenbi={self.in_sougenbi}, self.current_scene={self.current_scene}")
            sleep(1)
            detect_count += 1
            if detect_count >= 3:
                break
        
        self.goto_scene(NewSougenbiScene.NEW_SOUGENBI_SCENE_FOOLERY)

        # while 1:
        #     self.screenshot()
        #     if self.appear(self.I_S_FIRE_FOOLERY):
        #         break
        #     if self.appear_then_click(self.I_S_FIRE_FOOLERY, interval=1):
        #         continue
        self.in_sougenbi, self.current_scene = self.get_current_scene()
        logger.info(f" self.in_sougenbi={self.in_sougenbi}, self.current_scene={self.current_scene}")

        if self.current_scene != NewSougenbiScene.NEW_SOUGENBI_SCENE_FOOLERY:
            raise TaskEnd('Not in sougenbi')
        else:
            logger.info('In sougenbi')

        # sleep(0.5)
        # image_target = None
        # click_target = None
        # number_target = None
        # match con.new_sougenbi_config.new_sougenbi_class:
        #     case NewSougenbiClass.GREED:
        #         image_target = self.I_S_FIRE_GREED
        #         click_target = self.C_C_GREED
        #         number_target = self.O_S_GREED
        #     case NewSougenbiClass.Anger:
        #         image_target = self.I_S_FIRE_ANGER
        #         click_target = self.C_C_ANGER
        #         number_target = self.O_S_ANGER
        #     case NewSougenbiClass.Foolery:
        #         image_target = self.I_S_FIRE_FOOLERY
        #         click_target = self.C_C_FOOLERY
        #         number_target = self.O_S_FOOLERY
        #     case _:
        #         raise ValueError('Sougenbi class error')
        # self.check_lock(con.general_battle_config.lock_team_enable, self.I_S_TEAM_LOCK, self.I_S_TEAM_UNLOCK)
        # while 1:
        #     self.screenshot()
        #     if self.appear(self.I_S_FIRE_FOOLERY):
        #         break
        #     if self.click(self.C_C_FOOLERY, interval=0.5):
        #         pass

        logger.info('Click sougenbi in soul zones')

        # 开始循环
        while 1:
            self.screenshot()

            if not self.appear(self.I_S_FIRE_FOOLERY):
                logger.info('Not in sougenbi')
                continue
            if self.current_count >= con.new_sougenbi_config.limit_count:
                logger.info('NewSougenbi count limit out')
                break
            if datetime.now() - self.start_time >= self.limit_time:
                logger.info('NewSougenbi time limit out')
                break
            ticket = self.O_S_FOOLERY.ocr(self.device.image)
            if ticket == 0:
                logger.info('No ticket')
                break

            # 点击挑战
            logger.info(f'Click challenge:self.current_count={self.current_count}/{con.new_sougenbi_config.limit_count}, ticket={ticket}')
            while 1:
                self.screenshot()
                if self.appear_then_click(self.I_S_FIRE_FOOLERY, interval=1):
                    pass
                if not self.appear(self.I_S_FIRE_FOOLERY):
                    self.run_general_battle(config=con.general_battle_config)
                    break

        logger.info('NewSougenbi end')

        # 回去到探索大世界
        while 1:
            self.screenshot()
            if self.appear(self.I_CHECK_EXPLORATION):
                break
            if self.appear_then_click(self.I_UI_BACK_YELLOW, interval=1):
                continue
        logger.info('Back to exploration')

        if s_con.buff_enable:
            self.ui_get_current_page()
            self.ui_goto(page_main)
            self.open_buff()
            if s_con.buff_gold_50_click:
                self.gold_50(False)
            if s_con.buff_gold_100_click:
                self.gold_100(False)
            if s_con.buff_exp_50_click:
                self.exp_50(False)
            if s_con.buff_exp_100_click:
                self.exp_100(False)
            self.close_buff()

        self.set_next_run("NewSougenbi", success=True, finish=True)
        raise TaskEnd







if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device
    c = Config('test')
    d = Device(c)
    t = ScriptTask(c, d)
    t.screenshot()

    t.run()
    # print(t.appear(t.I_S_FOOLERY, threshold=0.97))

