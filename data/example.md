For example, given a target method `key_schedule_core`, a simplified version of the module hosting it is like this:

```python
    def aes_cbc_decrypt(data, key, iv):
        expanded_key = key_expansion(key)
        block_count = int(ceil(float(len(data)) / BLOCK_SIZE_BYTES))
        decrypted_data = []
        previous_cipher_block = iv
        for i in range(block_count):
            block = data[i * BLOCK_SIZE_BYTES:(i + 1) * BLOCK_SIZE_BYTES]
            block += [0] * (BLOCK_SIZE_BYTES - len(block))
            decrypted_block = aes_decrypt(block, expanded_key)
            decrypted_data += xor(decrypted_block, previous_cipher_block)
            previous_cipher_block = block
        decrypted_data = decrypted_data[:len(data)]
        return decrypted_data
        
    def key_expansion(data):
        data = data[:]
        rcon_iteration = 1
        key_size_bytes = len(data)
        expanded_key_size_bytes = (key_size_bytes // 4 + 7) * BLOCK_SIZE_BYTES
        while len(data) < expanded_key_size_bytes:
            temp = data[-4:]
            temp = key_schedule_core(temp, rcon_iteration)
            rcon_iteration += 1
            data += xor(temp, data[-key_size_bytes:4 - key_size_bytes])
            for _ in range(3):
                temp = data[-4:]
                data += xor(temp, data[-key_size_bytes:4 - key_size_bytes])
            if key_size_bytes == 32:
                temp = data[-4:]
                temp = sub_bytes(temp)
                data += xor(temp, data[-key_size_bytes:4 - key_size_bytes])
            for _ in range(3 if key_size_bytes == 32 else 2 if key_size_bytes ==
                24 else 0):
                temp = data[-4:]
                data += xor(temp, data[-key_size_bytes:4 - key_size_bytes])
        data = data[:expanded_key_size_bytes]
        return data


    def key_schedule_core(data, rcon_iteration):
        data = rotate(data)
        data = sub_bytes(data)
        data[0] = data[0] ^ RCON[rcon_iteration]
        return data
```

Through forward method-invocation analysis, we can extract one sequence `aes_cbc_decrypt->key_expansion->key_schedule_core` to enter the target method.

Therefore, we first construct the stage1 prompt according to this sequence:

```python
There is a python function 'key_schedule_core' in file aes. A simplified version of this file is

    def key_expansion(data):
        """
        Generate key schedule
        @param {int[]} data  16/24/32-Byte cipher key
        @returns {int[]}     176/208/240-Byte expanded key
        """
        data = data[:]
        rcon_iteration = 1
        key_size_bytes = len(data)
        expanded_key_size_bytes = (key_size_bytes // 4 + 7) * BLOCK_SIZE_BYTES
        while len(data) < expanded_key_size_bytes:
            temp = data[-4:]
            temp = key_schedule_core(temp, rcon_iteration)
            rcon_iteration += 1
            data += xor(temp, data[-key_size_bytes:4 - key_size_bytes])
            for _ in range(3):
                temp = data[-4:]
                data += xor(temp, data[-key_size_bytes:4 - key_size_bytes])
            if key_size_bytes == 32:
                temp = data[-4:]
                temp = sub_bytes(temp)
                data += xor(temp, data[-key_size_bytes:4 - key_size_bytes])
            for _ in range(3 if key_size_bytes == 32 else 2 if key_size_bytes ==
                24 else 0):
                temp = data[-4:]
                data += xor(temp, data[-key_size_bytes:4 - key_size_bytes])
        data = data[:expanded_key_size_bytes]
        return data

    def aes_cbc_decrypt(data, key, iv):
        """
        Decrypt with aes in CBC mode
        @param {int[]} data        cipher
        @param {int[]} key         16/24/32-Byte cipher key
        @param {int[]} iv          16-Byte IV
        @returns {int[]}           decrypted data
        """
        expanded_key = key_expansion(key)
        block_count = int(ceil(float(len(data)) / BLOCK_SIZE_BYTES))
        decrypted_data = []
        previous_cipher_block = iv
        for i in range(block_count):
            block = data[i * BLOCK_SIZE_BYTES:(i + 1) * BLOCK_SIZE_BYTES]
            block += [0] * (BLOCK_SIZE_BYTES - len(block))
            decrypted_block = aes_decrypt(block, expanded_key)
            decrypted_data += xor(decrypted_block, previous_cipher_block)
            previous_cipher_block = block
        decrypted_data = decrypted_data[:len(data)]
        return decrypted_data

    def key_schedule_core(data, rcon_iteration):
        data = rotate(data)
        data = sub_bytes(data)
        data[0] = data[0] ^ RCON[rcon_iteration]
        return data

What is the functionality of the function? Do not write any unit tests in your response.
```

Then we construct stage2 prompt according to the counter-examples:

```python
The test program below is designed to test the function 'key_schedule_core' through the call chain aes_cbc_decrypt->key_expansion->key_schedule_core. The content of the test program is

import timeout_decorator
import unittest
import youtube_dl.utils as module_1
import youtube_dl.aes as module_0

class Test(unittest.TestCase):
    @timeout_decorator.timeout(1)
    def test_case_13(self):
        try:
            bytes_0 = b'K39j5x9B+23D+3959B+23D+A'
            var_0 = module_1.bytes_to_intlist(bytes_0)
            var_1 = module_0.aes_cbc_decrypt(bytes_0, var_0, var_0)
        except BaseException:
            pass
    

if __name__ == "__main__":
    unittest.main()
Please generate new test programs that cover different scenarios or edge cases. The code should be self-contained and complete.
```

