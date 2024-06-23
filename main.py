import threading
from libs.stream import StreamLive
import pygame_menu
import pygame

# 主进程，负责启动追踪线程和图传线程
WIDTH = 1920
HEIGHT = 1080

# 图传线程上
def main():
    global running
    running = True

    def start_all_features():
        global running
        running = False
        menu.close()
        pygame.quit()
        stream_live = StreamLive(width=WIDTH, height=HEIGHT, tick=120, camera=0)
        s_thread = threading.Thread(target=stream_live.startStream)
        s_thread.start()

    def start_video_transmission():
        global running
        running = False
        menu.close()
        pygame.quit()
        stream_live = StreamLive(width=WIDTH, height=HEIGHT, tick=120, camera=0)
        s_thread = threading.Thread(target=stream_live.startStream)
        s_thread.start()

    def quit_program():
        global running
        running = False
        menu.close()
        pygame.quit()
        exit()


     # 加载中文字体
    font_path = "assest/font/HarmonyOS_Sans_SC_Regular.ttf"
    mytheme = pygame_menu.themes.THEME_BLUE.copy()
    mytheme.widget_font = font_path


    # 初始化Pygame和菜单
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.NOFRAME)
    menu = pygame_menu.Menu('LinLight Eye Tracker System', WIDTH, HEIGHT, theme=mytheme)

    menu.add.button('启动所有功能', start_all_features)
    menu.add.button('启动图传功能', start_video_transmission)
    menu.add.button('退出', quit_program)

    # 菜单循环
    while running:
        try:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    quit_program()
            if menu.is_enabled():
                menu.update(events)
                menu.draw(screen)
            pygame.display.flip()
        except pygame.error as e:
            print(f"Pygame error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
