# Huffman-Coding---python-2.7
A single or multiple file archiving program. No LZ77, different than DEFLATE, no data analysis either.

To compress an archive: 

  -o lets choose a name

  ./archive_huffman.py filestocompress1 .... filestocompressn -o namearchive

To decompress an archive:

  -d indicates decompression

  ./archive_huffman.py -d namearchive.zip
