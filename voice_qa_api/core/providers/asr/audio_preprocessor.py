"""
增强版音频预处理模块
包含：重采样、音量归一化、静音检测、降噪处理
"""
import os
import wave
import io
import numpy as np
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def resample_audio(
    data: np.ndarray,
    original_rate: int,
    target_rate: int = 16000
) -> np.ndarray:
    """
    高质量音频重采样
    
    Args:
        data: 音频数据数组
        original_rate: 原始采样率
        target_rate: 目标采样率，默认为16000Hz
    
    Returns:
        重采样后的音频数据
    """
    if original_rate == target_rate:
        return data
    
    # 使用线性插值进行重采样
    import scipy.signal
    
    duration = len(data) / original_rate
    num_samples = int(duration * target_rate)
    
    # 使用 resample 函数进行高质量重采样
    resampled = scipy.signal.resample(data, num_samples)
    return resampled


def normalize_audio(data: np.ndarray, target_peak: float = 0.95) -> np.ndarray:
    """
    音频音量归一化
    
    Args:
        data: 音频数据数组（float格式，范围[-1, 1]）
        target_peak: 目标峰值，默认为0.95
    
    Returns:
        归一化后的音频数据
    """
    max_val = np.max(np.abs(data))
    if max_val == 0:
        return data
    
    # 计算增益因子
    gain = target_peak / max_val
    
    # 应用增益
    normalized = data * gain
    
    # 限制在 [-1, 1] 范围内
    normalized = np.clip(normalized, -1.0, 1.0)
    
    return normalized


def detect_silence(
    data: np.ndarray,
    sample_rate: int = 16000,
    frame_duration_ms: int = 20,
    silence_threshold: float = 0.02,
    min_silence_duration_ms: int = 100
) -> Tuple[int, int]:
    """
    静音检测 - 基于能量检测
    
    Args:
        data: 音频数据数组（float格式）
        sample_rate: 采样率
        frame_duration_ms: 帧时长（毫秒）
        silence_threshold: 静音阈值
        min_silence_duration_ms: 最小静音时长（毫秒）
    
    Returns:
        (start_index, end_index): 有效音频的起始和结束索引
    """
    frame_size = int(sample_rate * frame_duration_ms / 1000)
    min_silence_frames = int(min_silence_duration_ms / frame_duration_ms)
    
    # 计算每帧的能量
    energy = []
    for i in range(0, len(data), frame_size):
        frame = data[i:i+frame_size]
        if len(frame) == 0:
            continue
        frame_energy = np.mean(np.abs(frame))
        energy.append(frame_energy)
    
    if len(energy) == 0:
        return 0, len(data)
    
    # 找到开头静音结束的位置
    start_frame = 0
    silence_count = 0
    for i, e in enumerate(energy):
        if e < silence_threshold:
            silence_count += 1
            if silence_count >= min_silence_frames:
                start_frame = i
        else:
            silence_count = 0
    
    # 找到结尾静音开始的位置
    end_frame = len(energy)
    silence_count = 0
    for i in range(len(energy)-1, -1, -1):
        if energy[i] < silence_threshold:
            silence_count += 1
            if silence_count >= min_silence_frames:
                end_frame = i
        else:
            silence_count = 0
    
    # 转换为样本索引
    start_idx = min(start_frame * frame_size, len(data))
    end_idx = min(end_frame * frame_size + frame_size, len(data))
    
    # 确保至少保留一些数据
    if end_idx - start_idx < frame_size * 2:
        start_idx = 0
        end_idx = len(data)
    
    return start_idx, end_idx


def spectral_subtraction(
    data: np.ndarray,
    sample_rate: int = 16000,
    noise_frame_count: int = 5,
    alpha: float = 2.0
) -> np.ndarray:
    """
    谱减法降噪
    
    Args:
        data: 音频数据数组（float格式）
        sample_rate: 采样率
        noise_frame_count: 用于估计噪声的帧数
        alpha: 降噪系数
    
    Returns:
        降噪后的音频数据
    """
    import scipy.fftpack
    
    frame_size = 512
    hop_size = frame_size // 2
    
    # 计算帧数
    num_frames = int(np.ceil(len(data) / hop_size))
    
    # 填充数据
    padded_data = np.zeros(num_frames * hop_size + frame_size)
    padded_data[:len(data)] = data
    
    # 使用前几帧估计噪声
    noise_estimate = np.zeros(frame_size)
    for i in range(min(noise_frame_count, num_frames)):
        frame = padded_data[i*hop_size:i*hop_size+frame_size]
        noise_estimate += np.abs(scipy.fftpack.fft(frame))
    
    noise_estimate /= min(noise_frame_count, num_frames)
    
    # 应用谱减法
    output_data = np.zeros_like(padded_data)
    
    for i in range(num_frames):
        start = i * hop_size
        end = start + frame_size
        
        frame = padded_data[start:end]
        
        # 计算频谱
        spectrum = scipy.fftpack.fft(frame)
        magnitude = np.abs(spectrum)
        phase = np.angle(spectrum)
        
        # 谱减法
        magnitude = np.maximum(magnitude - alpha * noise_estimate, 0)
        
        # 逆傅里叶变换
        denoised_spectrum = magnitude * np.exp(1j * phase)
        denoised_frame = np.real(scipy.fftpack.ifft(denoised_spectrum))
        
        # 重叠相加
        output_data[start:end] += denoised_frame * 0.5
    
    return output_data[:len(data)]


def process_audio(
    audio_data: bytes,
    original_rate: int,
    target_rate: int = 16000,
    normalize: bool = True,
    remove_silence: bool = True,
    denoise: bool = True
) -> Tuple[bytes, int]:
    """
    完整的音频预处理流程
    
    Args:
        audio_data: 原始音频数据（bytes，假设是16位PCM）
        original_rate: 原始采样率
        target_rate: 目标采样率
        normalize: 是否进行音量归一化
        remove_silence: 是否移除静音
        denoise: 是否进行降噪处理
    
    Returns:
        (processed_audio, sample_rate): 处理后的音频数据和采样率
    """
    try:
        # 1. 将 bytes 转换为 numpy 数组（假设是16位PCM）
        int_data = np.frombuffer(audio_data, dtype=np.int16)
        float_data = int_data.astype(np.float32) / 32767.0
        
        # 2. 重采样到目标采样率
        if original_rate != target_rate:
            float_data = resample_audio(float_data, original_rate, target_rate)
            logger.debug(f"重采样完成: {original_rate} -> {target_rate}")
        
        # 3. 降噪处理
        if denoise:
            try:
                float_data = spectral_subtraction(float_data, target_rate)
                logger.debug("降噪处理完成")
            except Exception as e:
                logger.warning(f"降噪失败，跳过: {e}")
        
        # 4. 音量归一化
        if normalize:
            float_data = normalize_audio(float_data)
            logger.debug("音量归一化完成")
        
        # 5. 静音检测与切除
        if remove_silence:
            start_idx, end_idx = detect_silence(float_data, target_rate)
            float_data = float_data[start_idx:end_idx]
            logger.debug(f"静音切除完成: {start_idx} -> {end_idx}")
        
        # 6. 转换回 bytes
        int_data = (float_data * 32767.0).astype(np.int16)
        processed_audio = int_data.tobytes()
        
        return processed_audio, target_rate
    
    except Exception as e:
        logger.error(f"音频预处理失败: {e}")
        return audio_data, original_rate


def wav_to_bytes(
    channels: int,
    sample_rate: int,
    sample_width: int,
    frames: bytes
) -> bytes:
    """
    将音频参数转换为 WAV 格式字节
    
    Args:
        channels: 声道数
        sample_rate: 采样率
        sample_width: 采样宽度（字节）
        frames: 音频帧数据
    
    Returns:
        WAV 格式的字节数据
    """
    output = io.BytesIO()
    with wave.open(output, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)
    return output.getvalue()


def bytes_to_wav_params(audio_bytes: bytes) -> Optional[dict]:
    """
    从 WAV 字节数据中提取参数
    
    Args:
        audio_bytes: WAV 格式的字节数据
    
    Returns:
        包含 channels, sample_rate, sample_width, frames 的字典，失败返回 None
    """
    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
            return {
                "channels": wf.getnchannels(),
                "sample_rate": wf.getframerate(),
                "sample_width": wf.getsampwidth(),
                "frames": wf.readframes(wf.getnframes())
            }
    except Exception as e:
        logger.error(f"解析 WAV 文件失败: {e}")
        return None


def ensure_mono_16khz(audio_bytes: bytes) -> bytes:
    """
    确保音频为单声道 16kHz 格式
    
    Args:
        audio_bytes: WAV 格式的字节数据
    
    Returns:
        单声道 16kHz 的 WAV 字节数据
    """
    params = bytes_to_wav_params(audio_bytes)
    if params is None:
        logger.warning("无法解析音频参数，返回原始数据")
        return audio_bytes
    
    channels = params["channels"]
    sample_rate = params["sample_rate"]
    sample_width = params["sample_width"]
    frames = params["frames"]
    
    # 如果已经是单声道 16kHz，直接返回
    if channels == 1 and sample_rate == 16000 and sample_width == 2:
        return audio_bytes
    
    # 转换为 numpy 数组
    if sample_width == 2:
        int_data = np.frombuffer(frames, dtype=np.int16)
    elif sample_width == 4:
        int_data = np.frombuffer(frames, dtype=np.int32).astype(np.int16)
    else:
        int_data = np.frombuffer(frames, dtype=np.int16)
    
    # 转换为单声道
    if channels > 1:
        int_data = int_data.reshape(-1, channels).mean(axis=1).astype(np.int16)
    
    # 重采样到 16kHz
    if sample_rate != 16000:
        float_data = int_data.astype(np.float32) / 32767.0
        float_data = resample_audio(float_data, sample_rate, 16000)
        int_data = (float_data * 32767.0).astype(np.int16)
    
    # 输出为 WAV
    output = io.BytesIO()
    with wave.open(output, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(int_data.tobytes())
    
    return output.getvalue()