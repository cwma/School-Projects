#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/slab.h>
#include <linux/errno.h>
#include <linux/types.h>
#include <linux/fs.h>
#include <linux/proc_fs.h>
#include <asm/uaccess.h>
#include <linux/string.h>
#include <linux/ioctl.h>

#define MAJOR_NUMBER 61
#define MAX_BYTES 4000000
#define SCULL_IOC_MAGIC 'k'
#define SCULL_IOC_MAXNR 14
#define SCULL_HELLO	_IO(SCULL_IOC_MAGIC, 1)

/* forward declaration */
int four_mb_open(struct inode *inode, struct file *filep);
int four_mb_release(struct inode *inode, struct file *filep);
ssize_t four_mb_read(struct file *filep, char *buf, size_t count, loff_t *f_pos);
ssize_t four_mb_write(struct file *filep, const char *buf, size_t count, loff_t *f_pos);
loff_t four_mb_seek(struct file *filep, loff_t f_pos, int seek_t);
long ioctl_example(struct file *filp, unsigned int cmd, unsigned long arg);
static void four_mb_exit(void);

/* definition of file_operation structure */
struct file_operations four_mb_fops = {
	read: four_mb_read,
	write: four_mb_write,
	open: four_mb_open,
	release: four_mb_release,
	llseek: four_mb_seek,
	unlocked_ioctl: ioctl_example
};

char *four_mb_data = NULL;
long *data_size = NULL;

int four_mb_open(struct inode *inode, struct file *filep)
{
	return 0; // always successful
}

int four_mb_release(struct inode *inode, struct file *filep)
{
	return 0; // always successful
}

ssize_t four_mb_read(struct file *filep, char *buf, size_t count, loff_t *f_pos)
{
    int to_read; 
    int read;
    to_read = *data_size - *f_pos;
    if(to_read > count) {
        to_read = count;
    }
    read = to_read - copy_to_user(buf, four_mb_data + *f_pos, to_read);
    *f_pos += read;
    return read;
}

ssize_t four_mb_write(struct file *filep, const char *buf, size_t count, loff_t *f_pos)
{
    int to_write;
    int written;
    to_write = MAX_BYTES - *f_pos;
    if(to_write > count) {
        to_write = count;
    }
    written = to_write - copy_from_user(four_mb_data + *f_pos, buf, to_write);
    *f_pos += written;
    printk(KERN_INFO "Thing: bytes writtens: %d\n", written);
    *data_size = *f_pos;
    return written;
}

static int four_mb_init(void)
{
	int result;

	result = register_chrdev(MAJOR_NUMBER, "4mb", &four_mb_fops);
	if (result < 0) {
		return result;
	}

	four_mb_data = kmalloc(MAX_BYTES, GFP_KERNEL);
	data_size = kmalloc(sizeof(long), GFP_KERNEL);
	if (!four_mb_data) {
		four_mb_exit();
		return -ENOMEM;
	}
	if (!data_size) {
		four_mb_exit();
		return -ENOMEM;
	}
	*data_size = 0;
	printk(KERN_ALERT "This is a 4mb byte device module\n");
	return 0;
}
 
loff_t four_mb_seek(struct file *filep, loff_t f_pos, int seek_t) 
{
    loff_t n_pos = 0;
    if(seek_t == 0) {
    	n_pos = f_pos;
    } else if(seek_t == 1) {
    	n_pos = filep->f_pos + f_pos;
    } else {
    	n_pos = *data_size - f_pos;
    }
    if(n_pos > *data_size) {
        n_pos = *data_size;
    }
    if(n_pos < 0) {
        n_pos = 0;
    }
    filep->f_pos = n_pos;
    return n_pos;
}

static void four_mb_exit(void)
{

	if (four_mb_data) {
		kfree(four_mb_data);
		four_mb_data = NULL;
	}
	if (data_size) {
		kfree(data_size);
		data_size = NULL;
	}
	unregister_chrdev(MAJOR_NUMBER, "4mb");
	printk(KERN_ALERT "4mb byte device module is unloaded\n");
}

long ioctl_example(struct file *filp, unsigned int cmd, unsigned long arg)
{
	int err = 0, tmp;
	int retval = 0;
	/*
	* extract the type and number bitfields, and don't decode
	* wrong cmds: return ENOTTY (inappropriate ioctl) before access_ok()
	*/
	if (_IOC_TYPE(cmd) != SCULL_IOC_MAGIC) return -ENOTTY;
	if (_IOC_NR(cmd) > SCULL_IOC_MAXNR) return -ENOTTY;
	/*
	* the direction is a bitmask, and VERIFY_WRITE catches R/W
	* transfers. `Type' is user‐oriented, while
	* access_ok is kernel‐oriented, so the concept of "read" and
	* "write" is reversed
	*/
	if (_IOC_DIR(cmd) & _IOC_READ)
		err = !access_ok(VERIFY_WRITE, (void __user *)arg, _IOC_SIZE(cmd));
	else if (_IOC_DIR(cmd) & _IOC_WRITE)
		err = !access_ok(VERIFY_READ, (void __user *)arg, _IOC_SIZE(cmd));
	if (err) return -EFAULT;
	switch(cmd) {
		case SCULL_HELLO:
			printk(KERN_WARNING "hello\n");
			break;
		default: /* redundant, as cmd was checked against MAXNR */
			return -ENOTTY;
	}
	return retval;
}

MODULE_LICENSE("GPL");
module_init(four_mb_init);
module_exit(four_mb_exit);