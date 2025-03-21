import pytest
import torch

from datasets import load_from_disk
from torch.utils.data import DataLoader
from transformers.models.gemma import GemmaConfig
from transformers.models.gemma import GemmaForCausalLM
from transformers.models.gemma2 import Gemma2Config
from transformers.models.gemma2 import Gemma2ForCausalLM
from transformers.models.llama import LlamaConfig
from transformers.models.llama import LlamaForCausalLM
from transformers.models.mistral import MistralConfig
from transformers.models.mistral import MistralForCausalLM
from transformers.models.mixtral import MixtralConfig
from transformers.models.mixtral import MixtralForCausalLM
from transformers.models.phi3 import Phi3Config
from transformers.models.phi3 import Phi3ForCausalLM
from transformers.models.qwen2 import Qwen2Config
from transformers.models.qwen2 import Qwen2ForCausalLM

from liger_kernel.transformers import apply_liger_kernel_to_gemma
from liger_kernel.transformers import apply_liger_kernel_to_gemma2
from liger_kernel.transformers import apply_liger_kernel_to_gemma3
from liger_kernel.transformers import apply_liger_kernel_to_granite
from liger_kernel.transformers import apply_liger_kernel_to_llama
from liger_kernel.transformers import apply_liger_kernel_to_mistral
from liger_kernel.transformers import apply_liger_kernel_to_mixtral
from liger_kernel.transformers import apply_liger_kernel_to_mllama
from liger_kernel.transformers import apply_liger_kernel_to_olmo2
from liger_kernel.transformers import apply_liger_kernel_to_phi3
from liger_kernel.transformers import apply_liger_kernel_to_qwen2
from liger_kernel.transformers import apply_liger_kernel_to_qwen2_5_vl
from liger_kernel.transformers import apply_liger_kernel_to_qwen2_vl
from test.utils import DEFAULT_DATASET_PATH
from test.utils import MiniModelConfig
from test.utils import assert_verbose_allclose
from test.utils import revert_liger_kernel_to_gemma
from test.utils import revert_liger_kernel_to_gemma2
from test.utils import revert_liger_kernel_to_gemma3
from test.utils import revert_liger_kernel_to_granite
from test.utils import revert_liger_kernel_to_llama
from test.utils import revert_liger_kernel_to_mistral
from test.utils import revert_liger_kernel_to_mixtral
from test.utils import revert_liger_kernel_to_mllama
from test.utils import revert_liger_kernel_to_olmo2
from test.utils import revert_liger_kernel_to_phi3
from test.utils import revert_liger_kernel_to_qwen2
from test.utils import revert_liger_kernel_to_qwen2_5_vl
from test.utils import revert_liger_kernel_to_qwen2_vl
from test.utils import set_seed
from test.utils import simple_collate_fn

try:
    # Mllama is only available in transformers>=4.45.0
    from transformers.models.mllama.configuration_mllama import MllamaTextConfig
    from transformers.models.mllama.modeling_mllama import MllamaForCausalLM

    MLLAMA_AVAILABLE = True
except ImportError:
    MLLAMA_AVAILABLE = False

try:
    # Qwen2-VL is only available in transformers>4.44.2
    from transformers.models.qwen2_vl.configuration_qwen2_vl import Qwen2VLConfig
    from transformers.models.qwen2_vl.modeling_qwen2_vl import Qwen2VLForConditionalGeneration

    QWEN2_VL_AVAILABLE = True
except ImportError:
    QWEN2_VL_AVAILABLE = False

try:
    # Qwen2.5-VL is only available in transformers>4.48.2
    from transformers.models.qwen2_5_vl.configuration_qwen2_5_vl import Qwen2_5_VLConfig
    from transformers.models.qwen2_5_vl.modeling_qwen2_5_vl import Qwen2_5_VLForConditionalGeneration

    QWEN2_5_VL_AVAILABLE = True
except ImportError:
    QWEN2_5_VL_AVAILABLE = False

try:
    from transformers.models.granite import GraniteConfig
    from transformers.models.granite import GraniteForCausalLM

    GRANITE_AVAILABLE = True
except ImportError:
    GRANITE_AVAILABLE = False

try:
    # OLMO2 is only available in transformers>=4.47.0
    from transformers.models.olmo2.configuration_olmo2 import Olmo2Config
    from transformers.models.olmo2.modeling_olmo2 import Olmo2ForCausalLM

    OLMO2_AVAILABLE = True
except ImportError:
    OLMO2_AVAILABLE = False

try:
    from transformers.models.gemma3.configuration_gemma3 import Gemma3TextConfig
    from transformers.models.gemma3.modeling_gemma3 import Gemma3ForCausalLM

    GEMMA3_AVAILABLE = True
except ImportError:
    GEMMA3_AVAILABLE = False

from liger_kernel.utils import infer_device

device = infer_device()

MINI_MODEL_SETUPS = {
    "mini_llama3": MiniModelConfig(
        liger_kernel_patch_func=apply_liger_kernel_to_llama,
        liger_kernel_patch_revert_func=revert_liger_kernel_to_llama,
        model_class=LlamaForCausalLM,
        mini_model_config=LlamaConfig(
            attention_bias=False,
            attention_dropout=0.0,
            # Special token ids/vocab size to match Mistral-7B tokenizer used to create the tokenized dataset
            # https://huggingface.co/mistralai/Mistral-7B-v0.1/blob/main/config.json
            bos_token_id=1,  # 128000
            eos_token_id=2,  # 128001
            hidden_act="silu",
            hidden_size=1024,  # 4096
            initializer_range=0.02,
            intermediate_size=2048,  # 14336
            max_position_embeddings=8192,
            num_attention_heads=8,  # 32
            num_hidden_layers=4,  # 32
            num_key_value_heads=2,  # 8
            pretraining_tp=1,
            rms_norm_eps=1e-5,
            rope_scaling=None,
            rope_theta=500000.0,
            tie_word_embeddings=False,
            use_cache=True,
            vocab_size=32000,  # 128256,
            # At rope backward
            # Eager produces incontiguous dq and dk
            # SDPA produces contiguous dq and incontiguous dk
            # Flash_attn produces contiguous dq and dk
            attn_implementation="sdpa",  # default value, pytorch native attention
        ),
    ),
    "mini_qwen2": MiniModelConfig(
        liger_kernel_patch_func=apply_liger_kernel_to_qwen2,
        liger_kernel_patch_revert_func=revert_liger_kernel_to_qwen2,
        model_class=Qwen2ForCausalLM,
        mini_model_config=Qwen2Config(
            attention_dropout=0.0,
            bos_token_id=1,  # 151643
            eos_token_id=2,  # 151643
            hidden_act="silu",
            hidden_size=896,
            initializer_range=0.02,
            intermediate_size=4864,
            max_position_embeddings=32768,  # 131072
            num_attention_heads=8,
            num_hidden_layers=4,
            num_key_value_heads=2,
            rms_norm_eps=1e-6,
            rope_theta=1000000.0,
            sliding_window=131072,
            tie_word_embeddings=True,
            use_cache=True,
            vocab_size=32000,  # 151936
            # At rope backward
            # Eager produces incontiguous dq and dk
            # SDPA produces contiguous dq and incontiguous dk
            # Flash_attn produces contiguous dq and dk
            attn_implementation="sdpa",  # default value, pytorch native attention
        ),
    ),
    "mini_phi3": MiniModelConfig(
        liger_kernel_patch_func=apply_liger_kernel_to_phi3,
        liger_kernel_patch_revert_func=revert_liger_kernel_to_phi3,
        model_class=Phi3ForCausalLM,
        mini_model_config=Phi3Config(
            attention_dropout=0.0,
            bos_token_id=1,
            eos_token_id=2,  # 32000
            hidden_act="silu",
            hidden_size=896,  # 3072
            initializer_range=0.02,
            intermediate_size=4864,  # 8192
            max_position_embeddings=4096,
            num_attention_heads=8,  # 32
            num_hidden_layers=4,  # 32
            num_key_value_heads=None,  # defaults to num_attention_heads
            rms_norm_eps=1e-5,
            rope_theta=10000.0,
            sliding_window=None,
            tie_word_embeddings=False,
            use_cache=True,
            vocab_size=32064,
            attn_implementation="eager",
        ),
    ),
    "mini_mistral": MiniModelConfig(
        liger_kernel_patch_func=apply_liger_kernel_to_mistral,
        liger_kernel_patch_revert_func=revert_liger_kernel_to_mistral,
        model_class=MistralForCausalLM,
        mini_model_config=MistralConfig(
            attention_dropout=0.0,
            bos_token_id=1,
            eos_token_id=2,
            hidden_act="silu",
            hidden_size=1024,
            initializer_range=0.02,
            intermediate_size=2048,
            max_position_embeddings=32768,
            num_attention_heads=8,
            num_hidden_layers=4,
            num_key_value_heads=2,
            rms_norm_eps=1e-5,
            rope_theta=10000.0,
            sliding_window=4096,
            tie_word_embeddings=False,
            use_cache=True,
            vocab_size=32000,
            attn_implementation="sdpa",
        ),
    ),
    "mini_mixtral": MiniModelConfig(
        liger_kernel_patch_func=apply_liger_kernel_to_mixtral,
        liger_kernel_patch_revert_func=revert_liger_kernel_to_mixtral,
        model_class=MixtralForCausalLM,
        mini_model_config=MixtralConfig(
            attention_dropout=0.0,
            bos_token_id=1,
            eos_token_id=2,
            hidden_act="silu",
            hidden_size=512,  # 4096
            initializer_range=0.02,
            intermediate_size=2048,  # 14336
            max_position_embeddings=32768,  # 32768
            num_attention_heads=8,  # 32
            num_hidden_layers=4,  # 32
            num_key_value_heads=2,  # 8
            rms_norm_eps=1e-5,
            rope_theta=10000.0,
            sliding_window=4096,
            tie_word_embeddings=False,
            use_cache=True,
            vocab_size=32000,
            attn_implementation="sdpa",
        ),
    ),
    "mini_gemma1": MiniModelConfig(
        liger_kernel_patch_func=apply_liger_kernel_to_gemma,
        liger_kernel_patch_revert_func=revert_liger_kernel_to_gemma,
        model_class=GemmaForCausalLM,
        mini_model_config=GemmaConfig(
            vocab_size=32000,  # 256000
            hidden_size=1024,  # 3072
            intermediate_size=2048,  # 24576
            num_hidden_layers=4,  # 28
            num_attention_heads=4,  # 16
            num_key_value_heads=4,  # 16
            head_dim=256,
            # gemma1 model config uses `hidden_act` and point it to gelu,
            # https://huggingface.co/google/gemma-7b/blob/main/config.json#L10
            # but in reality it's ignored and HuggingFace will use tanh approximation:
            # https://github.com/huggingface/transformers/blob/v4.40.1/src/transformers/models/gemma/modeling_gemma.py#L175
            hidden_act="gelu",
            max_position_embeddings=8192,
            initializer_range=0.02,
            rms_norm_eps=1e-06,
            use_cache=True,
            pad_token_id=0,
            # Special token ids/vocab size to match Mistral-7B tokenizer used to create the tokenized dataset
            # https://huggingface.co/mistralai/Mistral-7B-v0.1/blob/main/config.json
            bos_token_id=1,  # 128000
            eos_token_id=2,  # 128001
            tie_word_embeddings=True,
            rope_theta=10000.0,
            attention_bias=False,
            attention_dropout=0.0,
        ),
    ),
    "mini_gemma1.1": MiniModelConfig(
        liger_kernel_patch_func=apply_liger_kernel_to_gemma,
        liger_kernel_patch_revert_func=revert_liger_kernel_to_gemma,
        model_class=GemmaForCausalLM,
        mini_model_config=GemmaConfig(
            vocab_size=32000,  # 256000
            hidden_size=1024,  # 3072
            intermediate_size=2048,  # 24576
            num_hidden_layers=4,  # 28
            num_attention_heads=4,  # 16
            num_key_value_heads=4,  # 16
            head_dim=256,
            hidden_activation="gelu_pytorch_tanh",
            max_position_embeddings=8192,
            initializer_range=0.02,
            rms_norm_eps=1e-06,
            use_cache=True,
            pad_token_id=0,
            # Special token ids/vocab size to match Mistral-7B tokenizer used to create the tokenized dataset
            # https://huggingface.co/mistralai/Mistral-7B-v0.1/blob/main/config.json
            bos_token_id=1,  # 128000
            eos_token_id=2,  # 128001
            tie_word_embeddings=True,
            rope_theta=10000.0,
            attention_bias=False,
            attention_dropout=0.0,
        ),
    ),
    "mini_gemma2": MiniModelConfig(
        liger_kernel_patch_func=apply_liger_kernel_to_gemma2,
        liger_kernel_patch_revert_func=revert_liger_kernel_to_gemma2,
        model_class=Gemma2ForCausalLM,
        mini_model_config=Gemma2Config(
            vocab_size=32000,  # 256000
            hidden_size=1024,  # 3072
            intermediate_size=2048,  # 24576
            num_hidden_layers=4,  # 28
            num_attention_heads=4,  # 16
            num_key_value_heads=4,  # 16
            head_dim=256,
            hidden_activation="gelu_pytorch_tanh",
            max_position_embeddings=8192,
            initializer_range=0.02,
            rms_norm_eps=1e-06,
            use_cache=True,
            pad_token_id=0,
            # Special token ids/vocab size to match Mistral-7B tokenizer used to create the tokenized dataset
            # https://huggingface.co/mistralai/Mistral-7B-v0.1/blob/main/config.json
            bos_token_id=1,  # 128000
            eos_token_id=2,  # 128001
            tie_word_embeddings=True,
            rope_theta=10000.0,
            attention_bias=False,
            attention_dropout=0.0,
            attn_implementation="eager",
        ),
    ),
}

if GEMMA3_AVAILABLE:
    MINI_MODEL_SETUPS["mini_gemma3"] = MiniModelConfig(
        liger_kernel_patch_func=apply_liger_kernel_to_gemma3,
        liger_kernel_patch_revert_func=revert_liger_kernel_to_gemma3,
        model_class=Gemma3ForCausalLM,
        mini_model_config=Gemma3TextConfig(
            vocab_size=32000,  # 262144
            hidden_size=1024,  # 1152
            intermediate_size=2048,  # 6912
            num_hidden_layers=4,  # 26
            num_attention_heads=4,
            num_key_value_heads=1,
            head_dim=256,
            hidden_activation="gelu_pytorch_tanh",
            max_position_embeddings=8192,  # 32768
            initializer_range=0.02,
            rms_norm_eps=1e-06,
            use_cache=True,
            pad_token_id=0,
            bos_token_id=2,
            eos_token_id=1,
            tie_word_embeddings=True,
            rope_theta=10000.0,  # 1000000
            attention_bias=False,
            attention_dropout=0.0,
            attn_implementation="eager",
        ),
    )

if MLLAMA_AVAILABLE:
    MINI_MODEL_SETUPS["mini_mllama"] = MiniModelConfig(
        liger_kernel_patch_func=apply_liger_kernel_to_mllama,
        liger_kernel_patch_revert_func=revert_liger_kernel_to_mllama,
        model_class=MllamaForCausalLM,
        mini_model_config=MllamaTextConfig(
            bos_token_id=1,  # 128000
            eos_token_id=2,  # 128001
            pad_token_id=2,
            cross_attention_layers=None,
            dropout=0,
            hidden_act="silu",
            hidden_size=1024,  # 4096
            initializer_range=0.02,
            intermediate_size=2048,  # 14336
            max_position_embeddings=131_072,
            num_attention_heads=8,  # 32
            num_hidden_layers=4,  # 40
            num_key_value_heads=2,  # 8
            rms_norm_eps=1e-5,
            rope_scaling=dict(
                factor=8.0,
                high_freq_factor=4.0,
                low_freq_factor=1.0,
                original_max_position_embeddings=8192,
                rope_type="llama3",
            ),
            rope_theta=500_000,
            tie_word_embeddings=False,
            use_cache=True,
            vocab_size=32000,  # 128256,
            attn_implementation="sdpa",  # default value, pytorch native attention
        ),
    )

if QWEN2_VL_AVAILABLE:
    MINI_MODEL_SETUPS["mini_qwen2_vl"] = MiniModelConfig(
        liger_kernel_patch_func=apply_liger_kernel_to_qwen2_vl,
        liger_kernel_patch_revert_func=revert_liger_kernel_to_qwen2_vl,
        model_class=Qwen2VLForConditionalGeneration,
        mini_model_config=Qwen2VLConfig(
            attention_dropout=0.0,
            # bos and eos set to match the Mistral-7B tokenizer used to create the test dataset
            # https://huggingface.co/mistralai/Mistral-7B-v0.1/blob/main/config.json
            bos_token_id=1,  # 151643
            eos_token_id=2,  # 151645
            vision_start_token_id=32765,  # vocab_size - 5
            vision_end_token_id=32766,  # vocab_size - 4
            vision_token_id=32767,  # vocab_size - 3
            image_token_id=32768,  # vocab_size - 2
            video_token_id=32769,  # vocab_size - 1
            hidden_act="silu",
            hidden_size=1536,  # 8192
            initializer_range=0.02,
            intermediate_size=4864,  # 29568
            max_position_embeddings=32768,
            max_window_layers=4,  # 80
            num_attention_heads=12,  # 64
            num_hidden_layers=4,  # 80
            num_key_value_heads=2,  # 8
            rms_norm_eps=1e-6,  # 1e-5
            rope_theta=1000000.0,
            rope_scaling=dict(
                type="mrope",
                mrope_section=[16, 24, 24],  # (temporal, height, width)
            ),
            sliding_window=4096,
            tie_word_embeddings=False,
            use_cache=True,
            vocab_size=32768,  # 152064  # >32k, Mistral-7B tokenizer vocab size
            use_sliding_window=False,
            vision_config={
                "depth": 4,  # 32
                "embed_dim": 1280,
                "mlp_ratio": 4,
                "num_heads": 16,
                "in_chans": 3,
                "hidden_size": 128,  # 1536
                "patch_size": 14,
                "spatial_merge_size": 2,
                "spatial_patch_size": 14,
                "temporal_patch_size": 2,
            },
            attn_implementation="sdpa",
        ),
    )

if QWEN2_5_VL_AVAILABLE:
    MINI_MODEL_SETUPS["mini_qwen2_5_vl"] = MiniModelConfig(
        liger_kernel_patch_func=apply_liger_kernel_to_qwen2_5_vl,
        liger_kernel_patch_revert_func=revert_liger_kernel_to_qwen2_5_vl,
        model_class=Qwen2_5_VLForConditionalGeneration,
        mini_model_config=Qwen2_5_VLConfig(
            attention_dropout=0.0,
            # bos and eos set to match the Mistral-7B tokenizer used to create the test dataset
            # https://huggingface.co/mistralai/Mistral-7B-v0.1/blob/main/config.json
            bos_token_id=1,  # 151643
            eos_token_id=2,  # 151645
            vision_start_token_id=32765,  # vocab_size - 5
            vision_end_token_id=32766,  # vocab_size - 4
            vision_token_id=32767,  # vocab_size - 3
            image_token_id=32768,  # vocab_size - 2
            video_token_id=32769,  # vocab_size - 1
            hidden_act="silu",
            hidden_size=1536,  # 8192
            initializer_range=0.02,
            intermediate_size=4864,  # 29568
            max_position_embeddings=32768,
            max_window_layers=4,  # 80
            num_attention_heads=12,  # 64
            num_hidden_layers=4,  # 80
            num_key_value_heads=2,  # 8
            rms_norm_eps=1e-6,  # 1e-5
            rope_theta=1000000.0,
            rope_scaling=dict(
                type="mrope",
                mrope_section=[16, 24, 24],  # (temporal, height, width)
            ),
            sliding_window=4096,
            tie_word_embeddings=False,
            use_cache=True,
            vocab_size=32768,  # 152064  # >32k, Mistral-7B tokenizer vocab size
            use_sliding_window=False,
            vision_config={
                "depth": 4,  # 32
                "hidden_act": "silu",
                "hidden_size": 128,  # 1280
                "intermediate_size": 256,  # 3420
                "num_heads": 16,
                "in_chans": 3,
                "out_hidden_size": 128,  # 3584
                "patch_size": 14,
                "spatial_merge_size": 2,
                "spatial_patch_size": 14,
                "window_size": 112,
                "fullatt_block_indexes": [7, 15, 23, 31],
                "tokens_per_second": 2,
                "temporal_patch_size": 2,
            },
            attn_implementation="sdpa",
        ),
    )

if GRANITE_AVAILABLE:
    MINI_MODEL_SETUPS["mini_granite3"] = MiniModelConfig(
        liger_kernel_patch_func=apply_liger_kernel_to_granite,
        liger_kernel_patch_revert_func=revert_liger_kernel_to_granite,
        model_class=GraniteForCausalLM,
        mini_model_config=GraniteConfig(
            attention_bias=False,
            attention_dropout=0.0,
            # Special token ids/vocab size to match Mistral-7B tokenizer used to create the tokenized dataset
            # https://huggingface.co/mistralai/Mistral-7B-v0.1/blob/main/config.json
            bos_token_id=1,  # 128000
            eos_token_id=2,  # 128001
            hidden_act="silu",
            hidden_size=1024,  # 4096
            initializer_range=0.02,
            intermediate_size=2048,  # 14336
            max_position_embeddings=8192,
            num_attention_heads=8,  # 32
            num_hidden_layers=4,  # 32
            num_key_value_heads=2,  # 8
            pretraining_tp=1,
            rms_norm_eps=1e-5,
            rope_scaling=None,
            rope_theta=500000.0,
            tie_word_embeddings=False,
            use_cache=True,
            vocab_size=32000,  # 128256,
            logits_scaling=4.0,
            # At rope backward
            # Eager produces incontiguous dq and dk
            # SDPA produces contiguous dq and incontiguous dk
            # Flash_attn produces contiguous dq and dk
            attn_implementation="sdpa",  # default value, pytorch native attention
        ),
    )

if OLMO2_AVAILABLE:
    MINI_MODEL_SETUPS["mini_olmo2"] = MiniModelConfig(
        liger_kernel_patch_func=apply_liger_kernel_to_olmo2,
        liger_kernel_patch_revert_func=revert_liger_kernel_to_olmo2,
        model_class=Olmo2ForCausalLM,
        mini_model_config=Olmo2Config(
            bos_token_id=1,  # 128000
            eos_token_id=2,  # 128001
            pad_token_id=2,
            cross_attention_layers=None,
            dropout=0,
            hidden_act="silu",
            hidden_size=1024,  # 4096
            initializer_range=0.02,
            intermediate_size=2048,  # 14336
            max_position_embeddings=4096,
            num_attention_heads=8,  # 32
            num_hidden_layers=4,  # 40
            num_key_value_heads=2,  # 8
            rms_norm_eps=1e-5,
            rope_scaling=None,
            rope_theta=500_000,
            tie_word_embeddings=False,
            use_cache=True,
            vocab_size=32000,  # 128256,
            attn_implementation="sdpa",  # default value, pytorch native attention
        ),
    )


def create_model(model_name="mini_llama3"):
    """
    Create a mini version model
    The commented values are the original values
    """
    model_config = MINI_MODEL_SETUPS[model_name].mini_model_config
    model_class = MINI_MODEL_SETUPS[model_name].model_class
    return model_class(model_config)


def run_mini_model(
    model_name="mini_llama3",
    num_steps=100,
    dtype=torch.bfloat16,
    lr=1e-5,
    with_liger=False,
):
    # If we move it to the beginning of test_mini_model, the two runs are initialized with different weights.
    # This is due to RNG (Random Number Generator). The formula of RNG progression is x_(n+1) = (a * x_n + c) % m
    # Everytime RNG is used, like randomly initialzing weight, the RNG progresses to the next state.
    # Therefore, we have to reset RNG before we create the model to ensure the weight initialization started from the same RNG state.

    set_seed(42)

    revert_kwargs = {"model_config": MINI_MODEL_SETUPS[model_name]}
    if "mllama" in model_name:
        revert_kwargs["model_type"] = "causal_lm"

    if with_liger is True:
        kwargs = {
            "rope": True,
            "rms_norm": True,
        }

        model_supports_layer_norm = "qwen2_vl" in model_name
        if model_supports_layer_norm:
            kwargs["layer_norm"] = True

        if "gemma" in model_name:
            kwargs["geglu"] = True
        else:
            kwargs["swiglu"] = True

        kwargs["fused_linear_cross_entropy"] = False
        kwargs["cross_entropy"] = False

        MINI_MODEL_SETUPS[model_name].liger_kernel_patch_func(**kwargs)
    else:
        MINI_MODEL_SETUPS[model_name].liger_kernel_patch_revert_func(**revert_kwargs)

    model = create_model(model_name).to(dtype).to(device)
    train_dataset = load_from_disk(DEFAULT_DATASET_PATH)
    loader = DataLoader(train_dataset, batch_size=16, shuffle=False, collate_fn=simple_collate_fn)
    loader_iter = iter(loader)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)

    loss_list = []

    for i in range(num_steps):
        batch = next(loader_iter).to(model.device)
        optimizer.zero_grad()
        output = model(**batch)
        output.loss.backward()
        optimizer.step()
        print(f"Step {i}, Loss: {output.loss.item()}")
        loss_list.append(output.loss.item())

    MINI_MODEL_SETUPS[model_name].liger_kernel_patch_revert_func(**revert_kwargs)
    return {"loss": loss_list, "logits": output.logits, "model": model}


@pytest.mark.parametrize(
    "model_name, num_steps, lr, dtype, loss_atol, loss_rtol, logits_atol, logits_rtol, param_atol, param_rtol",
    [
        ("mini_llama3", 32, 1e-4, torch.float32, 1e-8, 2e-5, 1e-4, 1e-5, 5e-3, 1e-5),
        pytest.param(
            "mini_mllama",
            32,
            1e-4,
            torch.float32,
            1e-8,
            1e-5,
            5e-3,
            1e-5,
            5e-3,
            1e-5,
            marks=pytest.mark.skipif(
                not MLLAMA_AVAILABLE,
                reason="Mllama not available in this version of transformers",
            ),
        ),
        pytest.param(
            "mini_gemma3",
            32,
            1e-4,
            torch.float32,
            1e-8,
            1e-4,
            5e-3,
            1e-5,
            5e-3,
            1e-5,
            marks=pytest.mark.skipif(
                not GEMMA3_AVAILABLE,
                reason="Gemma3 not available in this version of transformers",
            ),
        ),
        ("mini_qwen2", 32, 1e-4, torch.float32, 1e-8, 1e-5, 5e-3, 1e-5, 5e-3, 1e-5),
        pytest.param(
            "mini_qwen2_vl",
            32,
            1e-4,
            torch.float32,
            1e-8,
            1e-5,
            5e-3,
            1e-5,
            5e-3,
            1e-5,
            marks=pytest.mark.skipif(
                not QWEN2_VL_AVAILABLE,
                reason="Qwen2-VL not available in this version of transformers",
            ),
        ),
        pytest.param(
            "mini_qwen2_5_vl",
            32,
            1e-4,
            torch.float32,
            1e-8,
            1e-5,
            5e-3,
            1e-5,
            5e-3,
            1e-5,
            marks=pytest.mark.skipif(
                not QWEN2_5_VL_AVAILABLE,
                reason="Qwen2.5-VL not available in this version of transformers",
            ),
        ),
        pytest.param(
            "mini_olmo2",
            32,
            1e-4,
            torch.float32,
            1e-8,
            1e-5,
            5e-3,
            1e-5,
            5e-3,
            1e-5,
            marks=pytest.mark.skipif(
                not OLMO2_AVAILABLE,
                reason="OLMO2 not available in this version of transformers",
            ),
        ),
        ("mini_phi3", 32, 1e-4, torch.float32, 1e-8, 1e-5, 5e-3, 1e-5, 5e-3, 1e-5),
        ("mini_mistral", 32, 1e-4, torch.float32, 1e-8, 1e-5, 5e-3, 1e-5, 5e-3, 1e-5),
        # TODO: mixtral is flaky so disable the test for now
        # ("mini_mixtral", 32, 1e-4, torch.float32, 5e-4, 1e-4, 5e-3, 1e-5, 1e-2, 1e-5),
        # Gemma 1.1 and 2 has more tolerance because currently, the kernel is not a perfect match
        ("mini_gemma1", 32, 1e-4, torch.float32, 1e-8, 1e-4, 5e-3, 1e-5, 5e-3, 1e-5),
        ("mini_gemma1.1", 32, 1e-4, torch.float32, 1e-8, 1e-4, 5e-3, 1e-5, 5e-3, 1e-5),
        ("mini_gemma2", 32, 1e-4, torch.float32, 1e-8, 1e-4, 5e-3, 1e-5, 5e-3, 1e-5),
        pytest.param(
            "mini_granite3",
            32,
            1e-4,
            torch.float32,
            1e-8,
            1e-4,
            5e-3,
            1e-5,
            5e-3,
            1e-5,
            marks=pytest.mark.skipif(
                not GRANITE_AVAILABLE,
                reason="Granite not available in this version of transformers",
            ),
        ),
    ],
)
def test_mini_model(
    model_name,
    num_steps,
    lr,
    dtype,
    loss_atol,
    loss_rtol,
    logits_atol,
    logits_rtol,
    param_atol,
    param_rtol,
):
    # Non-liger models should be initialized and tested first to avoid the module being overridden

    expected_output = run_mini_model(model_name=model_name, num_steps=num_steps, dtype=dtype, lr=lr)

    actual_output = run_mini_model(model_name=model_name, num_steps=num_steps, dtype=dtype, lr=lr, with_liger=True)

    # Compare every step of the loss
    assert_verbose_allclose(
        torch.tensor([expected_output["loss"]]),
        torch.tensor([actual_output["loss"]]),
        atol=loss_atol,
        rtol=loss_rtol,
    )

    # No logits are materialized
    # import pdb; pdb.set_trace()
    # Compare the logits from the last step
    assert_verbose_allclose(
        expected_output["logits"],
        actual_output["logits"],
        atol=logits_atol,
        rtol=logits_rtol,
    )

    # Compare the params from the last step
    # Iterate over the model's parameters and compare them
    for expected_param, actual_param in zip(
        expected_output["model"].named_parameters(),
        actual_output["model"].named_parameters(),
        strict=False,
    ):
        assert_verbose_allclose(expected_param[1], actual_param[1], atol=param_atol, rtol=param_rtol)
