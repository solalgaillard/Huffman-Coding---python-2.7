#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from pprint import pprint
from bitarray import bitarray
from math import ceil

class Huffman(object) :
    def __init__(self):
        self.prefix={}
        self.table_bitarray=bitarray()
        self.main_bitarray=bitarray()
        self.file_size=0
        self.table_size=0
        self.total_cost=0
        self.uncompressed=[]

    #Trouve le nbre de bits nécessaire pour enregistrer un nombre(au maximum sur 31 bits)
    def __pack_size(self, file_size):
        for i in xrange(1, 32):
            x = ceil(float(file_size)/(2**i-1))
            if x == 1:return i

    #Crée codes
    def __make_codes(self, node, code = '') :
        if isinstance(node[1], str) : self.prefix[node[1]] = code
        else :
            self.__make_codes(node[1], code + '0')
            self.__make_codes(node[2], code + '1')

    #Homogénéise l'arbre en arbre canonique
    def __to_canonical(self,prefix):
        code=0;prefix[0]=(prefix[0][0],('{:0'+str(prefix[0][1])+'b}').format(code))
        for x in xrange(1,len(prefix)):
            len_now=prefix[x][1];code = (code+1) << (len_now - len(prefix[x-1][1]))
            prefix[x]=(prefix[x][0], ('{:0'+str(len_now)+'b}').format(code))
        self.prefix=dict(zip([x[0] for x in prefix],[bitarray(x[1]) for x in prefix]))

    #Créé une table avec deux méthodes distinctes, on choisit la plus efficace
    def __pack_table(self,prefix) :
        prefix=[(x[0],len(x[1])) for x in prefix]
        self.__to_canonical(prefix)
        
        #1ère méthode:
        #On crée une liste de 256 items correspondant à toutes les combinaisons possibles sur un octet en ordre ascendant. A chaque emplacement, on inscrit la longueur du codage en bit à longueur variable (0 si vide). On pourra ainsi reconstituer tous les octets grâce à nos bits à longueur variable. La forme canonique permet de s'assurer de la correspondance du codage car la liste des prefixes a été organisé en ordre croissant.
        full_canonical_list=[]
        for z in xrange(0,256):
            if chr(z) in self.prefix:full_canonical_list=full_canonical_list+[len(self.prefix[chr(z)])]
            else: full_canonical_list=full_canonical_list+[0]
        #Petit gain d'espace, on ne gaspille pas un octet mais la taille maximum qu'il faut pour enregistrer le plus des codewords. On est obligé d'enregistrer sur 4 bits cette taille (au maximum 8 octets.)
        max_byte_size=self.__pack_size(max(full_canonical_list))
        write_to_bitarray = bitarray('0')+bitarray('{:04b}'.format(max_byte_size))
        for x in full_canonical_list:
            write_to_bitarray = write_to_bitarray+bitarray(('{:0'+str(max_byte_size)+'b}').format(x))
        # Enregistre la table et sa taille
        self.table_size = len(write_to_bitarray)
        self.table_bitarray = write_to_bitarray
        
        #2ème méthode:
        #On produit une seconde méthode où seront inscrits de manière séquentielles, le nbre de codewords correspondant à une longueur particulière. Nous n'avons pas besoin d'un octet pour stocker les plus petites longueurs car 2^1=2 possibilités max de codewords, 2^2=4,... Suivent ensuite les octets correspondants sous forme ASCII augmentée. On épuise le nombre de codewords d'une certaine longueur avant de passer à la longueur suivante.Ci-dessous un exemple de la forme de la liste. 
        #(nbre de codewords de longueur différentes) (0,0,4,5,..) ('a','b','c',...)      
        char_amt=[];char=[]
        max_size_prefix = max([len(x[1]) for x in prefix])
        for z in xrange(1, max_size_prefix+1): # de 1 à max car codage peut être sur un grand nombre de bits (+ qu'un octet)
            m=[i for i in prefix if len(i[1]) == z];char_amt.append(len(m)) #si len correspond à idx
            if len(m):char=char+[i[0] for i in m]#autre liste avec charactère
        char_amt=char_amt+char #regroupe les listes
        write_to_bitarray=bitarray('1')+bitarray(('{:05b}').format(max_size_prefix))#indice de méthode de compression + 5 bits pour inscrire la longueur max d'un codeword
        for x in xrange(0, max_size_prefix): #formate avec bits à longueur variable pour indiquer les longueurs car il ne peut y avoir plus de 2^1 charactère au niveau 1 de l'arbre, soit 2 bits, 2^2 charactères au niveau 2 de l'arbre, soit 3 bits, etc...
            #Ici on repasse sur un format 8 bits car nous sommes limités de toutes façons à encoder 256 formes différentes au maximum.
            if x+1>7:
                write_to_bitarray=write_to_bitarray+bitarray(('{:08b}').format(char_amt[x]))
            else:write_to_bitarray=write_to_bitarray+bitarray(('{:0'+str(x+2)+'b}').format(char_amt[x]))
        for x in xrange(max_size_prefix, len(char_amt)): #Pour les lettres codés sur un octet
            write_to_bitarray=write_to_bitarray+bitarray(('{:08b}').format(ord(char_amt[x])))

            
        table_size=len(write_to_bitarray)
        
        #Si cette méthode est plus efficace que la précédente, on l'utilise. Elle le sera la plupart du temps. Nous aurions pu aussi faire une troisième méthode qui réutilise la première mais en encadrant sa plage de codage entre le premier codeword et le dernier. Comme quoi, on peut toujours pousser plus loin. Par ailleurs, la table pourrait être elle-aussi encodé comme DEFLATE de Gzip mais on va pas devenir fou.
        if table_size < self.table_size :
            self.table_bitarray = write_to_bitarray
            self.table_size = table_size
        

    #décode la table et recompose prefixe
    def __unpack_table(self, full_bitarray):
        #1ère méthode
        if full_bitarray[:1] == bitarray('0'):
            byte_size=int(full_bitarray[1:5].to01(),2)
            t=[];truncated_array=full_bitarray[5:]
            for x in xrange(0, 256*byte_size, byte_size):
                t=t+[int(truncated_array[x:x+byte_size].to01(), 2)]
            for x in xrange(0, len(t)):
                if t[x] != 0 : self.prefix[chr(x)]=t[x]
            self.__to_canonical(sorted(self.prefix.items(), key=lambda x: (x[1],x[0])))
            self.table_size = 256*byte_size+5
            
        #deuxième méthode
        if full_bitarray[:1] == bitarray('1'):
            last_idx = 6 ; x = 1;m=[]
            #récupère la longueur max d'un codeword. On peut ensuite itérer sur toutes les longueurs.
            max_size_prefix = int(full_bitarray[1:last_idx].to01(),2)
            for i in xrange(1, max_size_prefix+1) :
                if x < 8: x = x + 1 #codage à longueur variable jusqu'à l'octet.
                m.append(int(full_bitarray[last_idx:last_idx+x].to01(),2))
                last_idx = last_idx+x
                
            char_bytes = sum(m)*8
            for i in xrange(0, char_bytes,8):
                m.append(chr(int(full_bitarray[last_idx+i:last_idx+i+8].to01(),2)))
        
            self.table_size = last_idx + char_bytes
            
            #bring m back to canonical
            self.prefix={}
            for x in xrange(0,max_size_prefix):
                for i in xrange(m[x]):
                    self.prefix[m[max_size_prefix]]=x+1
                    m.remove(m[max_size_prefix])
        
            self.__to_canonical(sorted(self.prefix.items(), key=lambda x: (x[1],x[0])))
            
            
    #Compresse Huffman
    def compress_huffman(self, aString) :
        frequency={}
        for x in aString : frequency[x]=frequency.get(x, 0) + 1
        H = zip(frequency.values(), frequency.keys())
        while H[1:] :
            left = min(H) ; H.remove(left) # get 1st lightest
            right = min(H) ; H.remove(right) # get 2nd lightest
            H.append((left[0] + right[0], left, right)) # sum frequencies and join nodes
        self.__make_codes(H[0])
        self.__pack_table(sorted(self.prefix.items(), key=lambda x: (len(x[1]),x[0])))
        self.main_bitarray=bitarray()#Car encode n'est pas destructif et ajoute au bitarray
        self.main_bitarray.encode(self.prefix, aString)

    #Decompress Huffman
    def decompress_huffman(self, aBitArray):
        self.__unpack_table(aBitArray)
        self.uncompressed=aBitArray[self.table_size:self.table_size+self.file_size].decode(self.prefix)
            
    #Zip un fichier mais n'écrit pas sur disque
    def __zip_to_file_aux(self, filename):
        file = open(filename, 'r')
        #5bits pour définir le nbre de bits pour stocker le nom, 5 bits pour la taille, on la lit ensuite
        filename = filename.split("/")[-1]
        if len(filename) > 31 : filename = filename[:31]
        whole_file=file.read()
        self.compress_huffman(filename+whole_file)
        self.file_size=len(self.main_bitarray)
        file_size_bit_nbr=self.__pack_size(self.file_size)
        write_to_bitarray= '{:05b}'.format(len(filename))+'{:05b}'.format(file_size_bit_nbr)+ '{:b}'.format(self.file_size)
        write_to_bitarray=bitarray(write_to_bitarray)+self.table_bitarray+self.main_bitarray
        
        self.total_cost = int(ceil((10+self.table_size+self.file_size+file_size_bit_nbr)/8.))
        print '\nFile: %s\nData Size: %sbits, Table Size: %sbits, File Header Size: %sbits\nTotal Size: %sbytes, Original Size: %sbytes\nCompression Ratio: %.2f\n' % (filename, self.file_size, self.table_size, 10+file_size_bit_nbr, self.total_cost, len(whole_file),float(len(whole_file))/self.total_cost)
        self.prefix={}#réinitialise pour les itérations suivantes
        return write_to_bitarray

    #Méthode pilote pour zipper. Itère sur plusieurs fichiers
    def zip_to_file(self, aList, filename):
        write_to_bitarray=bitarray()
        for x in aList:
            write_to_bitarray=write_to_bitarray + self.__zip_to_file_aux(x)
        file = open(filename+'.zip', 'wb+')
        write_to_bitarray.tofile(file)

    #Unzip et écrit sur disque tous les fichiers dans une archive.
    def __unzip_to_files_aux(self, filename):
        file = open(filename, 'rb')
        full_bitarray=bitarray()
        full_bitarray.fromfile(file)
        while full_bitarray:
            filename_size = int(full_bitarray[0:5].to01(),2)
        
            file_size_bit_nbr=int(full_bitarray[5:10].to01(),2)
            main_start = 10+file_size_bit_nbr
            self.file_size=int(full_bitarray[10:main_start].to01(),2)
            self.decompress_huffman(full_bitarray[main_start:])
            file_to_write=open(''.join(self.uncompressed[:filename_size]), 'wb+')
        
            file_to_write.write(''.join(self.uncompressed[filename_size:]))
            full_file=self.file_size+file_size_bit_nbr+10+self.table_size
        
            full_bitarray=full_bitarray[full_file:]
            print '%s from %s has been successfully decompressed.' % (''.join(self.uncompressed[:filename_size]), filename)
            file_to_write.close()
            if len(full_bitarray)<8:break;

    #Procède au dézippage de plusieurs archives.
    def unzip_to_files(self, aList):
        for x in aList:
            self.__unzip_to_files_aux(x)
    
        


            
if len(sys.argv) is 1 :
    exit('missing source-file name')

_o = False
unzip = False
filename = 'Archive'
huff=Huffman()
list_files=[]

for x in xrange(1, len(sys.argv)) :
    if _o :
        filename = sys.argv[x]
        _o = False
    elif sys.argv[x] == '-o':
        if x+1 > len(sys.argv) : print 'You forgot a filename'
        else : _o = True
    elif sys.argv[x] == '-d' : unzip = True
    else : list_files = list_files + [sys.argv[x]]
    
if unzip : huff.unzip_to_files(list_files)
else : huff.zip_to_file(list_files, filename)
