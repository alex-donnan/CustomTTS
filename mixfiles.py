#!/usr/bin/env python

# Mix two mono files to get a stereo file

import sys, wave, struct

def mix_files(a, b, c, amix = 0.5, bmix = 0.5, chann = 2, phase = -1.):
	f1 = wave.open(a, 'r')
	f2 = wave.open(b, 'r')

	r1, r2 = f1.getframerate(), f2.getframerate()
	if r1 != r2:
		print("Error: frame rates must be the same!")
		sys.exit(1)

	f3 = wave.open(c, 'w')
	f3.setnchannels(1)
	f3.setsampwidth(2)
	f3.setframerate(r1)
	f3.setcomptype('NONE', 'Not Compressed')
	frames = min(f1.getnframes(), f2.getnframes())

	print("Mixing files, total length %.2f s..." % (frames / float(r1)))
	d1 = f1.readframes(frames)
	d2 = f2.readframes(frames)
	for n in range(frames):
		if not n % (5 * r1): print(n // r1, 's')
		d3 = struct.pack('h',
				int(
					(amix * struct.unpack('h', d1[2*n:2*n+2])[0]) +
					(bmix * struct.unpack('h', d2[2*n:2*n+2])[0])
				)
			)
		f3.writeframesraw(d3)
	f3.close()

def mix_many_files(files, out, chann = 2, phase = -1.):
	if len(files) > 0:
		file_arr = [wave.open(w, 'r') for w in files]
		
		rate = file_arr[0].getframerate()
		if not all(w.getframerate() == rate for w in file_arr):
			print("Error: frame rates must be the same!")
			sys.exit(1)
		print(rate)

		output = wave.open(out, 'w')
		output.setnchannels(1)
		output.setsampwidth(2)
		output.setframerate(rate)
		output.setcomptype('NONE', 'Not Compressed')

		frames = file_arr[0].getnframes()
		frame_arr = [w.readframes(frames) for w in file_arr]
		print("Mixing files, total length %.2f s..." % (frames / float(rate)))

		for n in range(frames):
			if not n % (5 * rate):
				print(n // rate, 's')

			frame_value = 0
			for fr in frame_arr:
				frame_value += (struct.unpack('h', fr[2*n:2*n+2])[0]) / len(file_arr)
			frame_out = struct.pack('h', int(frame_value))

			output.writeframesraw(frame_out)
		output.close()
	else:
		print("No files provided, file mix failed.")