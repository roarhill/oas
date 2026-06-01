# This Python file uses the following encoding: utf-8
# @brief    Contiue to breed (重复点击蓝蛋/红蛋继续育成)
# @author   jackyhwei
# @note     draft version without full test
# github    https://github.com/roarhill/oas
from time import sleep
from datetime import time, datetime, timedelta
import random

from tasks.GameUi.game_ui import GameUi
from tasks.GameUi.page import page_main
from module.logger import logger
from module.exception import TaskEnd

from tasks.Component.GeneralBattle.general_battle import GeneralBattle

from tasks.ContinueBreed.assets import BreedAssets
from tasks.ContinueBreed.config import ContinueBreed, BreedConfig
from tasks.ContinueBreed.scene import BreedSceneDetector, BreedScene

class ScriptTask(GameUi, BreedSceneDetector):
# class ScriptTask(GameUi, ContinueBreed, BreedSceneDetector):
# class ScriptTask(GeneralBattle, GameUi, ContinueBreed, BreedSceneDetector):
# class ScriptTask(GeneralBattle, ContinueBreed, BreedSceneDetector):
# class ScriptTask(GameUi):

    def run(self) -> bool:
        self.MAX_ERROR_COUNT = 10

        continue_breed: ContinueBreed = self.config.continue_breed

        config: BreedConfig = continue_breed.breed_config
        continue_breed_times: int = config.continue_breed_times

        self.current_count = 0
        self.error_count = 0

        # 重复点击蓝蛋/红蛋继续育成
        while self.current_count < continue_breed_times:
            logger.info(f"continue_breed_times={self.current_count}")
            ramdom_time = random.randint(1, 3)
            sleep(ramdom_time/5)

            # 获取当前场景
            current_scene = self.get_current_scene(reuse_screenshot=False)
            match current_scene:
                case BreedScene.BREED_SCENE_CONFIRM:
                    self.current_count += 1
                    self.error_count = 0
                    self.ui_click_until_disappear(self.I_BREEDING_CONFIRM, interval=2)
                    logger.info(f"ocr={self.I_BREEDING_CONFIRM}")
                    continue
                case BreedScene.BREED_SCENE_CONTINUE:
                    self.error_count = 0
                    self.ui_click_until_disappear(self.I_CONTINUE_BREEDING, interval=2)
                    logger.info(f"ocr={self.I_CONTINUE_BREEDING}")
                    continue
                case _:
                    self.error_count += 1
                    logger.error(f"current_scene={current_scene}")
                    if self.error_count >= self.MAX_ERROR_COUNT:
                        logger.error(f"error_count={self.error_count} >= MAX_ERROR_COUNT={self.MAX_ERROR_COUNT}")
                        break

        self.goto_main()

        # self.set_next_run(task="ContinueBreed", target=now + 1)
        cd = timedelta(days=30)
        next_run = datetime.now() + cd

        # self.set_next_run(task='ContinueBreed', success=True, finish=False, target=next_run)
        self.set_next_run('ContinueBreed', finish=True, success=True)

        raise TaskEnd()

    def goto_main(self):
        """ 保持好习惯，一个任务结束了就返回庭院，方便下一任务的开始或者是出错重启

            任意庭院->道馆的界面返回庭院
        """
        while 1:
            self.screenshot()
            if self.appear(self.I_CHECK_MAIN):
                break
            if self.appear(self.I_BACK_BL):
                self.click(self.I_BACK_BL, interval=3)
                continue
            if self.appear(self.I_BACK_Y):
                self.click(self.I_BACK_Y, interval=3)
                continue

if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device

    c = Config('oas1')
    d = Device(c)
    t = ScriptTask(c, d)

    t.run()

    # t.check_layer('悲')

    from module.base.timer import timer
