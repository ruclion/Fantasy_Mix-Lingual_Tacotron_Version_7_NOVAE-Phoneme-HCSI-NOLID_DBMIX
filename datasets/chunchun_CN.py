from concurrent.futures import ProcessPoolExecutor
from functools import partial

import numpy as np
import os
from datasets import audio


def build_from_path_CN(hparams, speaker_num, lan_num, input_dir, use_prosody, mel_dir, linear_dir, wav_dir, n_jobs=12, tqdm=lambda x: x):
	"""
	待补充TODO...

	Args:
		- hparams: hyper parameters
		- input_dir: input directory that contains the files to prerocess
		- use_prosody: whether the prosodic structure labeling information will be used
		- mel_dir: output directory of the preprocessed speech mel-spectrogram dataset
		- linear_dir: output directory of the preprocessed speech linear-spectrogram dataset
		- wav_dir: output directory of the preprocessed speech audio dataset
		- n_jobs: Optional, number of worker process to parallelize across
		- tqdm: Optional, provides a nice progress bar

	Returns:
		- A list of tuple describing the train examples. this should be written to train.txt
	"""

	# We use ProcessPoolExecutor to parallelize across processes, this is just for
	# optimization purposes and it can be omited
	executor = ProcessPoolExecutor(max_workers=n_jobs)
	futures = []
	index = 1
	assert use_prosody is True
	with open(os.path.join(input_dir, 'metadata.txt'), encoding='utf-8') as f:
		for line in f:
			parts = line.strip().split('|')
			basename = parts[0]
			wav_path = os.path.join(input_dir, 'wavs_8k', '{}.wav'.format(basename))
			text = parts[1]
			out_name = 'chunchun_CN_' + basename
			# futures.append(executor.submit(partial(_process_utterance, mel_dir, linear_dir, wav_dir, basename, wav_path, text, speaker_num, lan_num, hparams)))
			futures.append(executor.submit(partial(_process_utterance, mel_dir, linear_dir, wav_dir, out_name, wav_path, text, speaker_num, lan_num, hparams)))
			index += 1

	return [future.result() for future in tqdm(futures) if future.result() is not None]


def _process_utterance(mel_dir, linear_dir, wav_dir, index, wav_path, text, speaker_num, lan_num, hparams):
	"""
	Preprocesses a single utterance wav/text pair

	this writes the mel scale spectogram to disk and return a tuple to write
	to the train.txt file

	Args:
		- mel_dir: the directory to write the mel spectograms into
		- linear_dir: the directory to write the linear spectrograms into
		- wav_dir: the directory to write the preprocessed wav into
		- index: the numeric index to use in the spectogram filename
		- wav_path: path to the audio file containing the speech input
		- text: text spoken in the input audio file
		- hparams: hyper parameters

	Returns:
		- A tuple: (audio_filename, mel_filename, linear_filename, time_steps, mel_frames, linear_frames, text)
	"""
	try:
		# Load the audio as numpy array
		wav = audio.load_wav(wav_path, sr=hparams.sample_rate)
	except FileNotFoundError: #catch missing wav exception
		print('file {} present in csv metadata is not present in wav folder. skipping!'.format(
			wav_path))
		return None

	#rescale wav
	if hparams.rescale:
		wav = wav / np.abs(wav).max() * hparams.rescaling_max

	#M-AILABS extra silence specific
	if hparams.trim_silence:
		wav = audio.trim_silence(wav, hparams)

	#Get spectrogram from wav
	ret = audio.wav2spectrograms(wav, hparams)
	if ret is None:
		return None
	out = ret[0]
	mel_spectrogram = ret[1]
	linear_spectrogram = ret[2]
	time_steps = ret[3]
	mel_frames = ret[4]

	# Write the spectrogram and audio to disk
	audio_filename = 'audio-{}.npy'.format(index)
	mel_filename = 'mel-{}.npy'.format(index)
	linear_filename = 'linear-{}.npy'.format(index)
	np.save(os.path.join(wav_dir, audio_filename), out.astype(np.float32), allow_pickle=False)
	np.save(os.path.join(mel_dir, mel_filename), mel_spectrogram.T, allow_pickle=False)
	np.save(os.path.join(linear_dir, linear_filename), linear_spectrogram.T, allow_pickle=False)

	# Return a tuple describing this training example
	return (audio_filename, mel_filename, linear_filename, time_steps, mel_frames, text, speaker_num, lan_num)
