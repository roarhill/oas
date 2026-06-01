from enum import Enum
from tasks.ContinueBreed.assets import BreedAssets
from tasks.base_task import BaseTask

class BreedScene(Enum):
    # 未知界面
    BREED_SCENE_UNKNOWN = 0
    # 继续
    BREED_SCENE_CONTINUE = 1
    # 确认
    BREED_SCENE_CONFIRM = 2

    def __str__(self):
        return self.name.title()


class BreedSceneDetector(BreedAssets, BaseTask):
    def get_current_scene(self, reuse_screenshot: bool = True) -> tuple[bool, BreedScene]:
        """
        检测当前场景
        """
        if not reuse_screenshot:
            self.screenshot()
        # 场景检测：继续
        if self.appear(self.I_CONTINUE_BREEDING, threshold=0.8):
            return BreedScene.BREED_SCENE_CONTINUE
        # 场景检测：确认
        if self.appear(self.I_BREEDING_CONFIRM, threshold=0.8):
            return BreedScene.BREED_SCENE_CONFIRM

        return BreedScene.BREED_SCENE_UNKNOWN
