from core import OmniClient, RAW_DIR, get_prompts_by_category
from core.augmentation import AugmentationPipeline

#
pipeline = AugmentationPipeline()
# 只跑倒伏状态增强
pipeline.run_edit_batch(RAW_DIR, "fallen_states", get_prompts_by_category("state"))


