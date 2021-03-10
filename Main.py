import sys


def main():
    with open("ortalis932.gmail.com.bin", "rb") as fd:
        # getting root block data
        block_size, pointers = get_block_data(fd, 0)
        blocks_data = {0: block_size}
        # using root block pointers to reveal all file blocks
        iterate_blocks(fd, blocks_data, pointers)
        sorted_blocks_data = sort_by_key_asc(blocks_data)
        collect_unused_memory(fd, sorted_blocks_data)


def get_block_data(f, offset):
    variant_bytes_size, block_size = get_variant_value_and_length(f, offset)
    pointers = get_block_pointers(f, offset + variant_bytes_size, block_size, offset + variant_bytes_size)
    return block_size, pointers


def iterate_blocks(fd, blocks_data, stack):
    """
    #Discover all existing blocks in fd by iterating over each block and adding the block pointers into
    #a stack, add to block_data the block offset and size and pop pointer by pointer until we can't reach any more blocks
    :param fd: file
    :param blocks_data: list to blocks by offset_in_file:block_size
    :param stack: initial list of pointers
    :return:
    """
    while len(stack):
        pointer = stack[-1]
        stack.pop()
        if pointer not in blocks_data:
            block_pointers = set_pointer_data_in_stack(fd, pointer, blocks_data, stack)
            for block_pointer in block_pointers:
                if block_pointer not in blocks_data:
                    set_pointer_data_in_stack(fd, pointer, blocks_data, stack)


def set_pointer_data_in_stack(fd, pointer, blocks_data, stack):
    block_size, block_pointers = get_block_data(fd, pointer)
    blocks_data.update({pointer: block_size})
    stack += block_pointers
    return block_pointers


def sort_by_key_asc(arr):
    return {k: arr[k] for k in sorted(arr)}


def collect_unused_memory(f, blocks_data):
    output = []
    f.seek(0)
    ptr_offset = list(blocks_data.keys())
    blocks_size = list(blocks_data.values())
    block_idx = 0
    while block_idx < len(blocks_data):
        cur_end_of_block_addr = ptr_offset[block_idx] + blocks_size[block_idx]
        f.seek(cur_end_of_block_addr)
        if block_idx != len(blocks_data) - 1:
            num_bytes_between_blocks = ptr_offset[block_idx + 1] - cur_end_of_block_addr
            if num_bytes_between_blocks > 0:
                unused_memory = f.read(num_bytes_between_blocks)
                output.append(str(unused_memory, 'utf-8'))
            block_idx += 1
        else:
            # should happen only once when we reach the end of the file
            # this handles the scenario of having unused memory after the last block, we read until the end of the file
            output.append(str(f.read(), 'utf-8'))
            break
    print(''.join(output))


def get_block_pointers(fd, offset, block_size, block_start_addr):
    fd.seek(block_start_addr)
    offset_in_block = 0
    pointers = []
    not_reached_end_of_block = offset_in_block != block_size - 1
    while not_reached_end_of_block:
        cur_ptr_size, ptr_val = get_variant_value_and_length(fd, offset + offset_in_block)
        # reached start of block payload
        if ptr_val == 0:
            break
        else:
            pointers.append(ptr_val)
        offset_in_block += cur_ptr_size
    return pointers


def get_variant_value_and_length(fd, offset):
    """
   #Calculate the number of bytes representing the next number in file from offset
   #The number is represented in Varint128 and based on the number of bytes in memory the value is
   #decoded using decode_varint_128 function
   :param fd: file
   :param offset: The offset in file where the number is present
   :return:
     number_of_bytes - numbers of bytes representing the number in file
     varint_value - The actual value
   """
    fd.seek(offset)
    single_byte = int.from_bytes(fd.read(1), sys.byteorder)
    number_of_bytes = 1

    # while msb is 1 this indicates that there are further bytes to come
    while single_byte & 0b10000000 != 0:
        number_of_bytes = number_of_bytes + 1

        single_byte = int.from_bytes(fd.read(1), sys.byteorder)

    # we want to reset the file offset and read the number_of_bytes representing the next number in file
    fd.seek(offset)
    varint_value = decode_varint_128(bytearray(fd.read(number_of_bytes)))
    return number_of_bytes, int(varint_value)


def decode_varint_128(byte_array, offset=0):
    needle = offset
    pair_count = 0
    result = 0
    while True:
        single_byte = byte_array[needle]

        # If first bit is 1
        if single_byte & 0b10000000 == 0:
            break

        # Remove first bit
        single_byte = single_byte & 0b01111111

        # Push number of bits we already have calculated
        single_byte = single_byte << (pair_count * 7)

        # Merge byte with result
        result = result | single_byte

        needle = needle + 1
        pair_count = pair_count + 1

    # Merge last byte with result
    single_byte = single_byte << (pair_count * 7)
    result = result | single_byte
    return result


if __name__ == "__main__":
    main()
