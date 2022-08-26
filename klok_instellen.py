import ledje
import sys

addr = int(sys.argv[1])

display = ledje.Ledje()

print(display._send_command(addr, 'G        '))
print(display.configure(addr))
