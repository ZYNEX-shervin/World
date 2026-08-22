"""
Input handling and control mapping
"""
import curses

class InputHandler:
    """Handles keyboard input"""
    
    def __init__(self, stdscr, renderer):
        self.stdscr = stdscr
        self.renderer = renderer
        self.running = True
    
    def handle_input(self):
        """Process keyboard input"""
        try:
            ch = self.stdscr.getch()
            
            if ch == -1:
                return True
            
            if ch == ord('q') or ch == ord('Q'):
                return False
            elif ch == 27:
                return False
            elif ch == ord('+') or ch == ord('='):
                self.renderer.zoom_in()
            elif ch == ord('-'):
                self.renderer.zoom_out()
            elif ch == ord('r') or ch == ord('R'):
                self.renderer.reset()
            elif ch == ord('p') or ch == ord('P'):
                self.renderer.cycle_projection()
            elif ch == ord('h') or ch == ord('H'):
                self.renderer.toggle_status()
            elif ch == ord('c') or ch == ord('C'):
                self.renderer.toggle_color()
            elif ch == ord('t') or ch == ord('T'):
                self.renderer.toggle_antarctica()
            elif ch == curses.KEY_UP or ch == ord('w') or ch == ord('W'):
                self.renderer.pan('north')
            elif ch == curses.KEY_DOWN or ch == ord('s') or ch == ord('S'):
                self.renderer.pan('south')
            elif ch == curses.KEY_LEFT or ch == ord('a') or ch == ord('A'):
                self.renderer.pan('west')
            elif ch == curses.KEY_RIGHT or ch == ord('d') or ch == ord('D'):
                self.renderer.pan('east')
            
            return True
        except KeyboardInterrupt:
            return False
        except:
            return True
