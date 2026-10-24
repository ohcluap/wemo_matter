/* Experimental offline decoder, not an installer. Output is untrusted until
 * exit status and the expected executable digest have both been checked.
 * Never executes output or opens device/flash paths itself. */
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <unistd.h>
#include <lzma.h>

static ssize_t read_retry(int fd, void *buf, size_t length)
{
    ssize_t n;
    do { n = read(fd, buf, length); } while (n < 0 && errno == EINTR);
    return n;
}

int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    int fd = open(argv[1], O_RDONLY);
    if (fd < 0) return 3;
    lzma_stream stream = LZMA_STREAM_INIT;
    int result = 4;
    unsigned char input[4096], output[4096];
    size_t consumed = 0, produced = 0;
    int eof = 0;
    if (lzma_stream_decoder(&stream, 2U * 1024U * 1024U, 0) != LZMA_OK)
        goto done;
    for (;;) {
        if (!stream.avail_in && !eof) {
            ssize_t n = read_retry(fd, input, sizeof(input));
            if (n < 0) goto done;
            consumed += (size_t)n;
            if (consumed > 1024U * 1024U) goto done;
            eof = n == 0;
            stream.next_in = input;
            stream.avail_in = (size_t)n;
        }
        stream.next_out = output;
        stream.avail_out = sizeof(output);
        lzma_ret status = lzma_code(&stream, eof ? LZMA_FINISH : LZMA_RUN);
        size_t count = sizeof(output) - stream.avail_out;
        if (count > 2U * 1024U * 1024U - produced) goto done;
        produced += count;
        if (status != LZMA_OK && status != LZMA_STREAM_END) goto done;
        for (size_t offset = 0; offset < count;) {
            ssize_t n = write(STDOUT_FILENO, output + offset, count - offset);
            if (n < 0 && errno == EINTR) continue;
            if (n <= 0) goto done;
            offset += (size_t)n;
        }
        if (status == LZMA_STREAM_END) {
            /* Exactly one CRC32 stream, no concatenated stream or trailing bytes. */
            if (stream.avail_in || lzma_get_check(&stream) != LZMA_CHECK_CRC32)
                goto done;
            unsigned char trailing;
            if (read_retry(fd, &trailing, 1) != 0) goto done;
            result = 0;
            break;
        }
    }
done:
    lzma_end(&stream);
    close(fd);
    return result;
}
