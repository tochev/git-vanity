/*
 * Part of git-vanity, a tool for finding git commit hash prefixes
 * Copyright (C) 2014  Tocho Tochev <tocho AT tochev DOT net>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 *
 *
 * Inspired by John the Rippers opencl code
 *
 * Refer to https://en.wikipedia.org/wiki/SHA-1#SHA-1_pseudocode
 */

#pragma OPENCL EXTENSION cl_khr_byte_addressable_store : enable

// sha1 constants
#define K0  0x5A827999
#define K1  0x6ED9EBA1
#define K2  0x8F1BBCDC
#define K3  0xCA62C1D6

#define SWAP32(n) (rotate(n & 0x00FF00FF, 24U)|(rotate(n, 8U) & 0x00FF00FF))

/*
 * sha1_prefix_search - searches for sha1 sum of the data with particular prefix
 *
 * preprocessed_message is in 64 byte chunks (includes the orig message length)
 * message_size size of the message (divisible by 64)
 * target - 160bits, zero padded after the real target
 * precisions bits - the bits of target to be compared
 * offset - where in the message to write the hex dump of (start+gid)
 * start is the start to which we add the gid, change the message if uint is not long enough
 * result[] = {found is found, the start+gid that matches target}
 */
__kernel void sha1_prefix_search(
        __global const uchar * preprocessed_message,
        const uint message_size,
        __global const uint * target,
        const uint precision_bits,
        const uint offset,
        const ulong start,
        __global ulong * result
    ) {
    uint t;
    uint W[16], temp, A,B,C,D,E;
    uint counter_words;

    const uint gid = get_global_id(0);

    // init vars
    uint H[5] = {0x67452301,
                 0xEFCDAB89,
                 0x98BADCFE,
                 0x10325476,
                 0xC3D2E1F0};

    const uchar TO_HEX[16] = {'0', '1', '2', '3', '4', '5', '6', '7',
                                      '8', '9', 'A', 'B', 'C', 'D', 'E', 'F'};

    __global const uint * chunk=(__global const uint *)preprocessed_message;
    __global const uint * stop = chunk + (message_size >> 2);
    __global const uint * offset_area_start = chunk + (offset >> 2);

    const ulong current = start + gid;

    // init special_words;
    uchar special_words[20];
    for (t=0; t < 20; t++) {
        if ((t < (offset & 0x3)) || (t >= ((offset & 0x3)+16))) {
            special_words[t] = preprocessed_message[(offset & (0xFFFFFFFF << 2)) +t];
        } else {
            special_words[t] = TO_HEX[(current >> (60 - ((t - (offset & 0x3)) << 2))) & 0xF];
        }
    }


    for (chunk=chunk; chunk < stop; chunk += 16) {

        // initialize boxes
        for (t = 0 ; t < 16 ; t++) {
            if ((offset_area_start <= (chunk + t)) &&
                ((chunk + t) - offset_area_start <= 4)) {
                W[t] = ((const uint *)special_words)[(chunk + t) - offset_area_start];
            } else {
                W[t] = chunk[t];
            }
            W[t] = SWAP32(W[t]);
        }

// algorithm
  A = H[0];
  B = H[1];
  C = H[2];
  D = H[3];
  E = H[4];

#undef R
#define R(t)                                              \
(                                                         \
    temp = W[(t -  3) & 0x0F] ^ W[(t - 8) & 0x0F] ^       \
           W[(t - 14) & 0x0F] ^ W[ t      & 0x0F],        \
    ( W[t & 0x0F] = rotate((int)temp,1) )                 \
)

#undef P
#define P(a,b,c,d,e,x)                                    \
{                                                         \
    e += rotate((int)a,5) + F(b,c,d) + K + x; b = rotate((int)b,30);\
}

#ifdef NVIDIA
#define F(x,y,z)	(z ^ (x & (y ^ z)))
#else
#define F(x,y,z)	bitselect(z, y, x)
#endif
#define K 0x5A827999

  P( A, B, C, D, E, W[0]  );
  P( E, A, B, C, D, W[1]  );
  P( D, E, A, B, C, W[2]  );
  P( C, D, E, A, B, W[3]  );
  P( B, C, D, E, A, W[4]  );
  P( A, B, C, D, E, W[5]  );
  P( E, A, B, C, D, W[6]  );
  P( D, E, A, B, C, W[7]  );
  P( C, D, E, A, B, W[8]  );
  P( B, C, D, E, A, W[9]  );
  P( A, B, C, D, E, W[10] );
  P( E, A, B, C, D, W[11] );
  P( D, E, A, B, C, W[12] );
  P( C, D, E, A, B, W[13] );
  P( B, C, D, E, A, W[14] );
  P( A, B, C, D, E, W[15] );
  P( E, A, B, C, D, R(16) );
  P( D, E, A, B, C, R(17) );
  P( C, D, E, A, B, R(18) );
  P( B, C, D, E, A, R(19) );

#undef K
#undef F

#define F(x,y,z) (x ^ y ^ z)
#define K 0x6ED9EBA1

  P( A, B, C, D, E, R(20) );
  P( E, A, B, C, D, R(21) );
  P( D, E, A, B, C, R(22) );
  P( C, D, E, A, B, R(23) );
  P( B, C, D, E, A, R(24) );
  P( A, B, C, D, E, R(25) );
  P( E, A, B, C, D, R(26) );
  P( D, E, A, B, C, R(27) );
  P( C, D, E, A, B, R(28) );
  P( B, C, D, E, A, R(29) );
  P( A, B, C, D, E, R(30) );
  P( E, A, B, C, D, R(31) );
  P( D, E, A, B, C, R(32) );
  P( C, D, E, A, B, R(33) );
  P( B, C, D, E, A, R(34) );
  P( A, B, C, D, E, R(35) );
  P( E, A, B, C, D, R(36) );
  P( D, E, A, B, C, R(37) );
  P( C, D, E, A, B, R(38) );
  P( B, C, D, E, A, R(39) );

#undef K
#undef F

#ifdef NVIDIA
#define F(x,y,z)	((x & y) | (z & (x | y)))
#else
#define F(x,y,z)	(bitselect(x, y, z) ^ bitselect(x, 0U, y))
#endif
#define K 0x8F1BBCDC

  P( A, B, C, D, E, R(40) );
  P( E, A, B, C, D, R(41) );
  P( D, E, A, B, C, R(42) );
  P( C, D, E, A, B, R(43) );
  P( B, C, D, E, A, R(44) );
  P( A, B, C, D, E, R(45) );
  P( E, A, B, C, D, R(46) );
  P( D, E, A, B, C, R(47) );
  P( C, D, E, A, B, R(48) );
  P( B, C, D, E, A, R(49) );
  P( A, B, C, D, E, R(50) );
  P( E, A, B, C, D, R(51) );
  P( D, E, A, B, C, R(52) );
  P( C, D, E, A, B, R(53) );
  P( B, C, D, E, A, R(54) );
  P( A, B, C, D, E, R(55) );
  P( E, A, B, C, D, R(56) );
  P( D, E, A, B, C, R(57) );
  P( C, D, E, A, B, R(58) );
  P( B, C, D, E, A, R(59) );

#undef K
#undef F

#define F(x,y,z) (x ^ y ^ z)
#define K 0xCA62C1D6

  P( A, B, C, D, E, R(60) );
  P( E, A, B, C, D, R(61) );
  P( D, E, A, B, C, R(62) );
  P( C, D, E, A, B, R(63) );
  P( B, C, D, E, A, R(64) );
  P( A, B, C, D, E, R(65) );
  P( E, A, B, C, D, R(66) );
  P( D, E, A, B, C, R(67) );
  P( C, D, E, A, B, R(68) );
  P( B, C, D, E, A, R(69) );
  P( A, B, C, D, E, R(70) );
  P( E, A, B, C, D, R(71) );
  P( D, E, A, B, C, R(72) );
  P( C, D, E, A, B, R(73) );
  P( B, C, D, E, A, R(74) );
  P( A, B, C, D, E, R(75) );
  P( E, A, B, C, D, R(76) );
  P( D, E, A, B, C, R(77) );
  P( C, D, E, A, B, R(78) );
  P( B, C, D, E, A, R(79) );

#undef K
#undef F

        // final switch
        H[0] = A + H[0];
        H[1] = B + H[1];
        H[2] = C + H[2];
        H[3] = D + H[3];
        H[4] = E + H[4];

    } // end loop

    // Check if prefix is correct and return if not
    counter_words = precision_bits/32;
    for (t = 0; t < counter_words; t++) {
        if (target[t] != H[t]) {
            return;
        }
    }
    if (counter_words < 5 && (precision_bits % 32)) {
        if (target[counter_words]
                !=
            (H[counter_words] & (0xFFFFFFFF << ((counter_words+1)*32 - precision_bits)))) {
            return;
        }
    }

    // WE FOUND IT :)
    // we do not care about sync too much since the write is atomic
    if (!result[0]) {
        result[0] = 1;
        result[1] = current;
    }
}
