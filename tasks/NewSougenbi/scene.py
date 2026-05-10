from enum import Enum

from module.config.config import Config
from module.device.device import Device
from module.logger import logger
from tasks.Component.GeneralBattle.assets import GeneralBattleAssets
from tasks.Dokan.assets import DokanAssets
from tasks.NewSougenbi.assets import NewSougenbiAssets
from tasks.Orochi.assets import OrochiAssets
from tasks.OrochiNew.assets import OrochiNewAssets
from tasks.base_task import BaseTask

class NewSougenbiScene(Enum):
    # 通用界面
    NEW_COMMON_SCENE_UNKNOWN = 0
    NEW_COMMON_SCENE_MAIN = 1
    NEW_COMMON_SCENE_EXPLORATION = 2
    NEW_COMMON_SCENE_SOUL = 3
    NEW_COMMON_SCENE_SOUGENBI = 4

    # 业原火界面
    NEW_SOUGENBI_SCENE_GREED = 1001 # 贪
    NEW_SOUGENBI_SCENE_ANGER_ = 1002 # 嗔
    NEW_SOUGENBI_SCENE_FOOLERY = 1003 # 痴
    NEW_SOUGENBI_SCENE_FIGHTING = 1004 # 战斗中

    def __str__(self):
        return self.name.title()

    def __value__(self):
        return self.value

class ScenePathConfig:
    """
    场景路径配置文件
    定义场景间的跳转关系
    """
    _instance = None
    _config = {
        "scene_paths": {
            "NEW_COMMON_SCENE_MAIN": {
                "NEW_COMMON_SCENE_EXPLORATION": "I_PATH_SCENE_MAIN_TO_EXPLORATION"
            },
            "NEW_COMMON_SCENE_EXPLORATION": {
                "NEW_COMMON_SCENE_SOUL": "I_PATH_SCENE_EXPLORATION_TO_SOUL"
            },
            "NEW_COMMON_SCENE_SOUL": {
                "NEW_COMMON_SCENE_SOUGENBI": "I_PATH_SCENE_SOUL_TO_SOUGENBI"
            },
            "NEW_COMMON_SCENE_SOUGENBI": {
                "NEW_SOUGENBI_SCENE_FOOLERY": "I_PATH_SCENE_SOUGENBI_TO_FOOLERY"
            }
        }
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_path_asset(self, from_scene: str, to_scene: str) -> str:
        """
        获取从from_scene到to_scene的路径资源名
        """
        paths = self._config.get("scene_paths", {})
        scene_paths = paths.get(from_scene, {})
        return scene_paths.get(to_scene, "")

    def build_fullpath(self, current_scene: NewSougenbiScene, target_scene: NewSougenbiScene) -> list:
        """
        构建从current_scene到target_scene的完整点击路径
        """
        if current_scene == target_scene:
            return []
        
        logger.info(f"current_scene={current_scene} target_scene={target_scene}")

        result = []
        current = current_scene
        visited = set()

        while current != target_scene:
            if current in visited:
                raise ValueError(f"Circular path detected at {current}")
            visited.add(current)

            asset_name = self.get_path_asset(current.name, target_scene.name)
            if asset_name:
                result.append(getattr(NewSougenbiAssets, asset_name))
                break

            for next_scene_name, next_asset in self._config["scene_paths"].get(current.name, {}).items(): # type: ignore
                next_scene = NewSougenbiScene[next_scene_name]
                result.append(getattr(NewSougenbiAssets, next_asset))
                current = next_scene
                break
            else:
                raise ValueError(f"No path found from {current} to {target_scene}")

        logger.info(f"build_fullpath={result}")

        return result
    



class NewSougenbiSceneDetector(NewSougenbiAssets, BaseTask, GeneralBattleAssets, OrochiNewAssets):

    def __init__(self, config: Config = None, device: Device = None): # type: ignore
        super().__init__(config, device)
        self.fullpath = {
            NewSougenbiScene.NEW_COMMON_SCENE_MAIN,
            NewSougenbiScene.NEW_COMMON_SCENE_EXPLORATION,
            NewSougenbiScene.NEW_COMMON_SCENE_SOUL,
            NewSougenbiScene.NEW_COMMON_SCENE_SOUGENBI,
            NewSougenbiScene.NEW_SOUGENBI_SCENE_FOOLERY,
        }
        self._path_config = ScenePathConfig()

    def goto_scene(self, scene: NewSougenbiScene, from_scene: NewSougenbiScene = None): # type: ignore
        """
        跳转到指定场景
        @param scene: 目标场景
        @param from_scene: 起始场景，默认从当前位置检测
        """
        if scene not in self.fullpath:
            raise ValueError(f"scene={scene} not in fullpath")
        
        if from_scene is None:
            _, from_scene = self.get_current_scene()
        
        path = self._path_config.build_fullpath(from_scene, scene)
        for asset in path:
            logger.info(f"goto_scene={asset}")
            self.screenshot()
            self.click(asset)
    
    def get_current_scene(self, reuse_screenshot: bool = True) -> tuple[bool, NewSougenbiScene]:
        """
        检测当前场景
        @type reuse_screenshot: object
        @return 从道馆地图开始,及其后面的所有道馆界面,都返回True
                一般界面,如庭院,式神录等 都返回False
        """
        if not reuse_screenshot:
            self.screenshot()

        # logger.info(f"get_current_scene={reuse_screenshot}")
        
        if self.appear(self.I_SCENE_MAIN):
            return True, NewSougenbiScene.NEW_COMMON_SCENE_MAIN # 主界面
        
        if self.appear(self.I_SCENE_EXPLORATION):
            return True, NewSougenbiScene.NEW_COMMON_SCENE_EXPLORATION # 探索界面
        

        # if self.appear(self.I_SCENE_SOUGENBI_GREED):
        #     return True, NewSougenbiScene.NEW_SOUGENBI_SCENE_GREED # 贪

        # if self.appear(self.I_SCENE_SOUGENBI_ANGER):
        #     return True, NewSougenbiScene.NEW_SOUGENBI_SCENE_ANGER_ # 嗔

        if self.appear(self.I_SCENE_SOUGENBI_FOOLERY):
            return True, NewSougenbiScene.NEW_SOUGENBI_SCENE_FOOLERY # 痴  

        if self.appear(self.I_SCENE_SOUL):
            return True, NewSougenbiScene.NEW_COMMON_SCENE_SOUL # 灵魂界面

        if self.appear(self.I_SCENE_SOUGENBI_FIGHTING):
            return True, NewSougenbiScene.NEW_SOUGENBI_SCENE_FIGHTING # 战斗中
        
        # 各种战斗结算界面
        if self.appear(self.I_OROCHI_SUCCEED2) or self.appear(self.I_OROCHI_SUCCEED):
            self.click(DokanAssets.C_DOKAN_RANDOM_CLICK_AREA2)
            return True, NewSougenbiScene.NEW_SOUGENBI_SCENE_FIGHTING # 战斗中
        
        return False, NewSougenbiScene.NEW_COMMON_SCENE_UNKNOWN