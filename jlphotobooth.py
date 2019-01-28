#!/usr/bin/python

import time, datetime, os, sys 
import subprocess as sub
import pygame
import pygbutton
import traceback
import GIFImage_ext
import RPi.GPIO as GPIO
import piexif

#***************VARIABLES******************
#Display settings
display_width = 1024
display_height = 600

#Flags
flag_upload_to_dropbox_immediately = False
flag_fullscreen = True
flag_use_pi_blaster_pwm = True
flag_show_exif = False

#Paths
main_path = os.path.split(os.path.abspath(__file__))[0]
assets_path = os.path.join(main_path, 'assets')
scripts_path = os.path.join(main_path, 'scripts')
photo_save_path = "/home/pi/photobooth_images/"
montage_save_path = "/home/pi/PB_archive/"
square_save_path = "/home/pi/PB_archive/"
gif_save_path = "/home/pi/PB_archive/"

#Camera
photos_taken = 0
last_image_taken_filename = ""
sequence_in_progress = False
photo_in_progress = False
photo_taken_success = False
sequence_filenames = []
spot_power = 0.7

#Montage
images_in_a_montage = 4
last_montage_created_filename = ""

#Square
images_in_a_square = 1
last_square_created_filename = ""

#Gif
images_in_a_gif = 6
last_gif_created_filename = ""

#Images
current_loaded_image_data = None
current_image = 0
current_image_exif = None
image_count = 0;
object_list = [] #list of preloaded images
last_image_number = 0

#Process
continue_loop = True
delay_time = 0.05
change_ticks = 0
homescreen_cycle = 0
homescreen_cycle_speed = 10000 #In milliseconds

# GPIO setup
bounceMillis = 800 #waits 800 ms before noticing another button press
flash_time = .1 #led flash time
BTN_A = 24
BTN_B = 25
LED_BTN_A = 23
LED_BTN_B = 22
LED_POSE = 18
LED_SPOT = 17
BTN_A_ACTIVE = False
BTN_B_ACTIVE = False

#***************FUNCTIONS******************
def APressed(channel):
    #Check button is still being pressed (helps deal with debounce callback issues)
    #Alternatively, can try this: https://raspberrypi.stackexchange.com/a/76738
    print("Button A callback triggered!")
    time.sleep(0.1)
    if GPIO.input(BTN_A) == 1:
      print("Button A press event detected, but button is not down, so ignoring...")
    elif sequence_in_progress:
      print("Button A pressed, but photo already in progress, so ignoring...")
    else:
      print("Button A pressed!")
      #snd_btn.play()
      CaptureMontage()

    global BTN_A_ACTIVE
    BTN_A_ACTIVE = False
    
def BPressed(channel):
	  #Check button is still being pressed (helps deal with debounce callback issues)
    print("Button B callback triggered!")
    time.sleep(0.1)
    if GPIO.input(BTN_B) == 1:
      print("Button B press event detected, but button is not down, so ignoring...")
    elif sequence_in_progress:
      print("Button B pressed, but photo already in progress, so ignoring...")
    else:
      print("Button B pressed!")
      #snd_btn.play()
      RenderImage(screen_one_photo_start)
      CaptureSquare()
      #CaptureGif()

    global BTN_B_ACTIVE
    BTN_B_ACTIVE = False

def LightsFlash(iterations, brightness = 1):
    index = 0

    print('[LED] Flashing lights!')

    #Flash LEDs for x iterations
    while(index<iterations):
        LightBrightness(LED_POSE,brightness)
        LightBrightness(LED_SPOT,0)
        time.sleep(flash_time)
        LightBrightness(LED_POSE,0)
        LightBrightness(LED_SPOT,brightness)
        time.sleep(flash_time)
        index = index + 1

    #Finish in an off state
    LightBrightness(LED_POSE,0)
    LightBrightness(LED_SPOT,0)

def LightBrightness(pin, val):
    if flag_use_pi_blaster_pwm:
        if val < 0 or val > 1:
            print('[ERROR] Brightness value %f out of range: must be in [0, 1].' % val)
            return
        #print('[LED] Setting brightness on pin %d to %f' % (pin, val))
        os.system('echo "%d=%f" > /dev/pi-blaster' % (pin, val))
    else:
        GPIO.output(pin, round(val))

def LoadNewImage():
    # after new image has been downloaded from the camera
    # it must be loaded into the object list and displayed on the screen
    global image_count
    global last_image_number
    global current_image
    global current_image_exif

    try:
      capture = pygame.transform.scale(pygame.image.load(photo_save_path + last_image_taken_filename).convert(),(display_width,display_height))
    except:
      print("[ERROR] Could not load image [%s]", last_image_taken_filename)
      return

    screen.blit(capture,(0,0))

    #Get Exif data
    try:
      exif = piexif.load(photo_save_path + last_image_taken_filename)
      current_image_exif = "f"+str(float(exif["Exif"][33437][0])/exif["Exif"][33437][1])+" "+str(exif["Exif"][33434][0])+"/"+str(exif["Exif"][33434][1])
      print("[CAMERA] Exif data for photo: %s" % current_image_exif)
      #for ifd in ("0th", "Exif", "GPS", "1st"):
      #  for tag in current_image_exif[ifd]:
      #      print(ifd, tag, piexif.TAGS[ifd][tag]["name"], current_image_exif[ifd][tag])
    except:
      print("[ERROR] Could not get Exif data for photo")
      current_image_exif = ""

    last_image_number = image_count
    current_image = last_image_number
    image_count = image_count + 1

    RenderOverlay()
    pygame.display.update()

def ShowImage(image_name, with_overlay = True):
    # load and show a specific image on screen (include full path)
    global current_loaded_image_data

    # Load image in the global image variable
    #current_loaded_image_data = pygame.transform.scale(pygame.image.load(image_name).convert(),(display_width,display_height))
    current_loaded_image_data = aspect_scale(pygame.image.load(image_name).convert(),(display_width,display_height))
    
    #Center image
    imgRect = current_loaded_image_data.get_rect()
    imgRect.center = ((display_width/2),(display_height/2))

    #Clear background
    background = pygame.Surface((display_width,display_height))#size
    background.fill(black)
    screen.blit(background,(0,0))#position

    #Show image
    screen.blit(current_loaded_image_data,imgRect)
    #object_list.append(current_loaded_image_data)

    #Show overlay if required
    if with_overlay:
        RenderOverlay()
    pygame.display.update()

def ShowGIF(image_name):
    # load and show a specific animated gif on screen (include full path)
    gif = GIFImage_ext.GIFImage(image_name)

    frame = 0
    while frame < images_in_a_gif:
      print("[RENDER] Rendering GIF frame " + str(frame))
      frame += 1
      gif.render(screen, (0, 0))
      RenderOverlay()
      pygame.display.update()
      gif.play()
      #pygame.display.flip()

def TakePicture():
    # executes the gphoto2 command to take a photo and download it from the camera
    global photo_taken_success
    global photos_taken
    global last_image_taken_filename
    global sequence_filenames
    photo_in_progress = True
    error = None

    #Make sure pose lighting is on at full brightness
    LightBrightness(LED_POSE,1)
    LightBrightness(LED_SPOT,spot_power)
    
    photo_taken_success = False

    MessageDisplay("SMILE")
    last_image_taken_filename = "photobooth" + GetDateTimeString() + ".jpg"
    take_pic_command = "gphoto2 --capture-image-and-download --filename " + photo_save_path + last_image_taken_filename
    error = False
    try:
      gpout = sub.check_output(take_pic_command, stderr=sub.STDOUT, shell=True)
    except sub.CalledProcessError as e:
      #print("command '{}' return with error (code {}): {}".format(e.cmd, e.returncode, e.output))
      print("[CAMERA] Failed to take photo")
      error = True
      #snd_channel2.play(snd_beep_down)
      gpout = e.output

    if not error: 
      photo_taken_success = True
      print("[CAMERA] Photo taken")
      photos_taken = photos_taken + 1
      sequence_filenames.append(last_image_taken_filename)
    elif "No camera found" in gpout:
      print("[ERROR][CAMERA] Camera not found")
      RenderImage(screen_error)
      LightsFlash(4)
      error = "OFF"
    elif "Error (-110" in gpout:
      print("[ERROR][CAMERA] Camera still busy (possibly failed to auto-focus)")
      MessageDisplay("RETRYING")
      time.sleep(2)
    else:
      print(gpout)
      print("[CAMERA] Unknown error")
    
    LightBrightness(LED_SPOT,0) #Darken spot lighting 
    LightBrightness(LED_POSE,0.5) #Dim pose lighting

    photo_in_progress = False

    #Return an error if one occurred
    return None if error == False else error

def CaptureMontage():
    global last_montage_created_filename
    global sequence_in_progress
    global sequence_filenames

    #Start mode
    RenderImage(screen_montage_start)
    LightsFlash(5, 0.4)

    sequence_in_progress = True
    sequence_filenames = []
    #snd_beep_down.play()
    #RenderOverlay(True, False)
    #MessageDisplay(str(images_in_a_montage) + " PHOTOS")
    CmdCleanup()
    time.sleep(2)
    RenderOverlay(True, False)

    snap = 0
    while snap < images_in_a_montage:
      print("[TIMER] Pose for photo!")
      MessageDisplay("READY")
      LightBrightness(LED_POSE,0.5)
      time.sleep(1.5)
      for i in range(5):
        #snd_beep_up.play()
        MessageDisplay(str(5-i))
        time.sleep(0.4)
      print("[CAMERA] SNAP!")
      if TakePicture() == "OFF":
        print("[SEQUENCE] Camera likely off, stopping sequence")
        ChangeTicks(15000)
        sequence_in_progress = False
        return
      if photo_taken_success == True:
        snap += 1
        LoadNewImage()
        if flag_show_exif:
          MessageDisplay(current_image_exif)
          time.sleep(3)

    print("Please wait while your photos are processed...")
    MessageDisplay("PROCESSING")
    last_montage_created_filename = "PB_MONT_" + GetDateTimeString() + ".jpg"
    #command = "sudo " + scripts_path + "/assemble_5x7.sh " + last_montage_created_filename
    print("Compositing images: " + str(sequence_filenames))
    command = "sudo " + scripts_path + "/assemble_5x7_special.sh " + last_montage_created_filename + " " + (photo_save_path + sequence_filenames[0]) + " " + (photo_save_path + sequence_filenames[1]) + " " + (photo_save_path + sequence_filenames[2]) + " " + (photo_save_path + sequence_filenames[3])
    print("Running command: " + command)
    sub.call(command, shell=True)
    LightBrightness(LED_POSE,0.2)
    ShowImage(montage_save_path + last_montage_created_filename, False)
    if flag_upload_to_dropbox_immediately:
      RenderOverlay()
      CmdUploadToDropbox(last_montage_created_filename)
    time.sleep(0.5)
    ShowImage(montage_save_path + last_montage_created_filename, False)
    time.sleep(3)
    RenderImage(screen_uploading)
    ChangeTicks(5000)
    sequence_in_progress = False

def CaptureSquare():
    global last_square_created_filename
    global sequence_in_progress
    global sequence_filenames

    #Start mode
    RenderImage(screen_one_photo_start)
    LightsFlash(5, 0.4)

    sequence_in_progress = True
    sequence_filenames = []
    #snd_beep_down.play()
    #RenderOverlay(True, False)
    #MessageDisplay(str(images_in_a_square) + " PHOTO")
    CmdCleanup()
    time.sleep(2)
    RenderOverlay(True, False)

    snap = 0
    while snap < images_in_a_square:
      print("[TIMER] Pose for photo!")
      MessageDisplay("READY")
      LightBrightness(LED_POSE,0.5)
      time.sleep(1.5)
      for i in range(5):
        #snd_beep_up.play()
        MessageDisplay(str(5-i))
        time.sleep(0.4)
      print("[CAMERA] SNAP!")
      if TakePicture() == "OFF":
        print("[SEQUENCE] Camera likely off, stopping sequence")
        ChangeTicks(15000)
        sequence_in_progress = False
        return
      if photo_taken_success == True:
        snap += 1
        LoadNewImage()
        if flag_show_exif:
          MessageDisplay(current_image_exif)
          time.sleep(3)

    print("Please wait while your photo is processed...")
    MessageDisplay("PROCESSING")
    last_square_created_filename = "PB_SQ_" + GetDateTimeString() + ".jpg"
    #command = "sudo " + scripts_path + "/assemble_square.sh " + last_square_created_filename
    print("Compositing images: " + str(sequence_filenames))
    command = "sudo " + scripts_path + "/assemble_square_special.sh " + last_square_created_filename + " " + (photo_save_path + sequence_filenames[0])
    print("Running command: " + command)
    sub.call(command, shell=True)
    LightBrightness(LED_POSE,0.2)
    ShowImage(square_save_path + last_square_created_filename, False)
    if flag_upload_to_dropbox_immediately:
      RenderOverlay()
      CmdUploadToDropbox(last_square_created_filename)
    time.sleep(0.5)
    ShowImage(square_save_path + last_square_created_filename, False)
    time.sleep(3)
    RenderImage(screen_uploading)
    ChangeTicks(5000)
    sequence_in_progress = False

def CaptureGif():
    global last_gif_created_filename
    global sequence_in_progress

    sequence_in_progress = True
    sequence_filenames = []
    #snd_beep_down.play()
    RenderOverlay(True, False)
    MessageDisplay(str(images_in_a_gif) + " PHOTOS")
    time.sleep(2)

    snap = 0
    while snap < images_in_a_gif:
      print("[TIMER] Pose for photo!")
      MessageDisplay("READY")
      LightBrightness(LED_POSE,0.5)
      time.sleep(1.5)
      for i in range(5):
        #snd_beep_up.play()
        MessageDisplay(str(5-i))
        time.sleep(0.2)
      print("[CAMERA] SNAP!")
      if TakePicture() == "OFF":
        print("[SEQUENCE] Camera likely off, stopping sequence")
        ChangeTicks(15000)
        sequence_in_progress = False
        return
      if photo_taken_success == True:
        snap += 1
        LoadNewImage()
        if flag_show_exif:
          MessageDisplay(current_image_exif)
          time.sleep(3)

    print("Please wait while your photos are processed...")
    MessageDisplay("PROCESSING")
    last_gif_created_filename = "PB_" + GetDateTimeString() + ".gif"
    command = "sudo " + scripts_path + "/assemble_gif.sh " + last_gif_created_filename
    sub.call(command, shell=True)
    LightBrightness(LED_POSE,0.2)
    if flag_upload_to_dropbox_immediately:
      CmdUploadToDropbox(last_gif_created_filename)
    MessageDisplay("COMPLETE!")
    time.sleep(0.5)
    RenderImage(screen_uploading)
    ChangeTicks(5000)
    #ShowGIF(gif_save_path + last_gif_created_filename)
    sequence_in_progress = False

def CmdCleanup():
    #Clean up any stray photos from previous attmpts (in case of errors)
    command = "sudo " + scripts_path + "/cleanup_pre_shoot.sh"
    sub.call(command, shell=True)

def CmdUploadToDropbox(filename):
    MessageDisplay("UPLOADING")
    command = "sudo " + scripts_path + "/upload_to_dropbox.sh " + filename
    sub.call(command, shell=True)

def GetDateTimeString():
    #format the datetime for the time-stamped filename
    dt = str(datetime.datetime.now()).split(".")[0]
    clean = dt.replace(" ","_").replace(":","_")
    return clean

def RenderHomeScreen():
    global homescreen_cycle
    global sequence_in_progress
    global photo_in_progress

    #Only cycle homescreen if there isn't anything else happening
    if sequence_in_progress or photo_in_progress:
        return

    if homescreen_cycle == 0:
        RenderImage(screen_start)

    elif homescreen_cycle == 1:
        if last_montage_created_filename != "":
            ShowImage(montage_save_path + last_montage_created_filename, False)

    elif homescreen_cycle == 2:
        if last_square_created_filename != "":
            ShowImage(square_save_path + last_square_created_filename, False)

    else:
        print("[ERROR] Invalid homescreen_cycle")

    if homescreen_cycle < 2:
        homescreen_cycle += 1
    else:
        homescreen_cycle = 0

def RenderImage(image):
    screen.blit(image[0],image[1])#position

    pygame.display.update()

def RenderOverlay(clearBackground=False, fillWhite=False):
    #Clear whole screen by adding a blank background (if required)
    if clearBackground:
      background = pygame.Surface((display_width,display_height))#size
      background.fill(white if fillWhite else black) #black or white depending on argument
      screen.blit(background,(0,0))#position

    #frame
    screen.blit(overlay_frame[0],overlay_frame[1])

    #buttons
    #montage_button.draw(screen)
    #gif_button.draw(screen)
    #quit_button.draw(screen)

    pygame.display.update()

#Displaying messages on screen
#Source: https://pythonprogramming.net/displaying-text-pygame-screen/
def MessageDisplay(text):
    #Prepare text
    largeText = pygame.font.Font('freesansbold.ttf',80)
    TextSurf, TextRect = TextObjects(text, largeText)
    TextRect.center = (((display_width/2)+225),(display_height-80))
    #TextRect.right = display_width-5

    #Prepare background box
    #backgroundBox = pygame.Surface((TextRect.width, TextRect.height))#size
    #backgroundBox.fill(white)

    # Create a transparent surface.
    alpha_img = pygame.Surface(TextSurf.get_size(), pygame.SRCALPHA)
    # Fill it with white and the desired alpha value.
    alpha_img.fill((255, 255, 255, 140))
    # Blit the alpha surface onto the text surface and pass BLEND_RGBA_MULT.
    TextSurf.blit(alpha_img, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    #Add to screen and render
    #screen.blit(backgroundBox, TextRect)
    RenderOverlay()
    screen.blit(TextSurf, TextRect)
    pygame.display.update()

def TextObjects(text, font):
    textSurface = font.render(text, True, white)
    return textSurface, textSurface.get_rect()   

#Loading images and sounds
#Source: https://www.pygame.org/docs/tut/ChimpLineByLine.html
def LoadOverlayImage(name, colorkey=None):
    """Store overlay images in ../data subfolder"""
    fullname = os.path.join(assets_path, name)
    try:
        image = pygame.image.load(fullname)
    except pygame.error, message:
        print 'Cannot load image:', fullname
        raise SystemExit, message

    if colorkey is -2:
      image = image.convert_alpha()
    elif colorkey is not None:
        image = image.convert()
        if colorkey is -1:
            colorkey = image.get_at((0,0))
            print "Setting colorkey for image to: " + str(colorkey)
        #image.set_colorkey(colorkey, pygame.RLEACCEL)
        image.set_colorkey(colorkey)
    else:
        image = image.convert()

    return image, image.get_rect()

def LoadSound(name):
    """Store sounds in ../data subfolder"""
    class NoneSound:
        def play(self): pass
    if not pygame.mixer:
        return NoneSound()
    fullname = os.path.join(assets_path, name)
    try:
        sound = pygame.mixer.Sound(fullname)
    except pygame.error, message:
        print 'Cannot load sound:', wav
        raise SystemExit, message
    return sound

def ChangeTicks(waitTime):
    global change_ticks
    change_ticks = pygame.time.get_ticks() + waitTime

#Aspect Scale: Scaling surfaces keeping their aspect ratio
#Source: http://www.pygame.org/pcr/transform_scale/
def aspect_scale(img,(bx,by)):
    """ Scales 'img' to fit into box bx/by.
     This method will retain the original image's aspect ratio """
    ix,iy = img.get_size()
    if ix > iy:
        # fit to width
        scale_factor = bx/float(ix)
        sy = scale_factor * iy
        if sy > by:
            scale_factor = by/float(iy)
            sx = scale_factor * ix
            sy = by
        else:
            sx = bx
    else:
        # fit to height
        scale_factor = by/float(iy)
        sx = scale_factor * ix
        if sx > bx:
            scale_factor = bx/float(ix)
            sx = bx
            sy = scale_factor * iy
        else:
            sy = by

    return pygame.transform.scale(img, (int(sx),int(sy)))

#Limit a number between a range
#Source: https://stackoverflow.com/a/5996949
def clamp(n, minn, maxn):
    if n < minn:
        return minn
    elif n > maxn:
        return maxn
    else:
        return n

#***************END FUNCTIONS******************


#***************INITIAL SETUP******************

# drops other possible connections to the camera
# on every restart just to be safe
os.system("sudo pkill gvfs")
os.environ['SDL_VIDEO_WINDOW_POS'] = "0,0"

app_name = "Jimmy L Raspberry Pi Photobooth"

print app_name + " started"

time.sleep(2)

white = pygame.Color(255,255,255)
black = pygame.Color(0,0,0)

#pygame.mixer.pre_init(44100, -16, 2, 1024) #For sound
pygame.init()
pygame.display.set_caption(app_name)

#Initialise GPIO
GPIO.setmode(GPIO.BCM)
#Buttons (if buttons go between input and ground, then to set pull_up_down=GPIO.PUD_UP)
GPIO.setup(BTN_A, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BTN_B, GPIO.IN, pull_up_down=GPIO.PUD_UP)
#LEDs
GPIO.setup(LED_BTN_A, GPIO.OUT)
GPIO.setup(LED_BTN_B, GPIO.OUT)
GPIO.setup(LED_POSE, GPIO.OUT)
GPIO.setup(LED_SPOT, GPIO.OUT)
LightBrightness(LED_POSE,0)
LightBrightness(LED_SPOT,0)
GPIO.output(LED_BTN_A, True)
GPIO.output(LED_BTN_B, True)

#Bind GPIO events
#GPIO.add_event_detect(BTN_A,GPIO.FALLING,callback=APressed,bouncetime=bounceMillis)
#GPIO.add_event_detect(BTN_B,GPIO.FALLING,callback=BPressed,bouncetime=bounceMillis)
#Visual test
LightsFlash(4)
LightBrightness(LED_POSE,0)
LightBrightness(LED_SPOT,0)

if flag_fullscreen:
  screen = pygame.display.set_mode((display_width,display_height),pygame.FULLSCREEN)#FULLSCREEN
  pygame.mouse.set_visible(False)
else:
  screen = pygame.display.set_mode((display_width,display_height))#NOT FULLSCREEN
  pygame.mouse.set_visible(True)

#Overlay related
overlay_frame = LoadOverlayImage("screen-overlay.png",-2) #use png alpha for transparency
screen_start = LoadOverlayImage("screen-main.png")
screen_uploading = LoadOverlayImage("screen-uploading.png")
screen_error = LoadOverlayImage("screen-error.png")
screen_one_photo_start = LoadOverlayImage("screen-one-photo.png")
screen_montage_start = LoadOverlayImage("screen-four-photos.png")
#overlay_frame = LoadOverlayImage("overlay.png",(255,61,233))
#overlay_frame = LoadOverlayImage("overlay.png",-1) #get colourkey from pixel 0,0
montage_button = pygbutton.PygButton((10,(display_height-45),80,30), "montage")
gif_button = pygbutton.PygButton((90,(display_height-45),80,30), "gif")
quit_button = pygbutton.PygButton((170,(display_height-45),80,30), "quit")

RenderHomeScreen()

#Sound related
#snd_beep_up = LoadSound("tone-beep-tri-up.wav")
#snd_beep_down = LoadSound("tone-beep-tri-down.wav")
#snd_btn = LoadSound("tone-beep-lower-slower.wav")
#snd_btn.play()


#***************MAIN LOOP******************
print "START MAIN LOOP"

try:
    while(continue_loop):
        #PyGame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print "Quitting..."
                continue_loop = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_c and pygame.key.get_mods() & pygame.KMOD_CTRL:
                  print "[GUI] Pressed CTRL-C as an event. Quitting..."
                  continue_loop = False

                elif event.key == pygame.K_f:
                  if screen.get_flags() & pygame.FULLSCREEN:
                      pygame.display.set_mode((display_width,display_height))
                      pygame.mouse.set_visible(True)
                      print "[GUI] Switching to window"
                      RenderHomeScreen()
                  else:
                      pygame.display.set_mode((display_width,display_height), pygame.FULLSCREEN)
                      pygame.mouse.set_visible(False)
                      print "[GUI] Switching to fullscreen"
                      RenderHomeScreen()

                elif event.key == pygame.K_EQUALS:
                      spot_power = clamp((spot_power + 0.1), 0, 1)
                      print("[SETTINGS] Increasing spotlight power to: [%s]", spot_power)
                      LightBrightness(LED_SPOT,spot_power)
                      time.sleep(0.5)
                      LightBrightness(LED_SPOT,0)

                elif event.key == pygame.K_MINUS:
                      if spot_power < 0.11:
                          spot_power = clamp((spot_power - 0.01), 0, 1)
                      else:
                          spot_power = clamp((spot_power - 0.1), 0, 1)
                      print("[SETTINGS] Decreasing spotlight power to: [%s]", spot_power)
                      LightBrightness(LED_SPOT,spot_power)
                      time.sleep(0.5)
                      LightBrightness(LED_SPOT,0)

                elif event.key == pygame.K_m:
                      CaptureMontage()

                elif event.key == pygame.K_s:
                      CaptureSquare()

                elif event.key == pygame.K_g:
                      CaptureGif()

                elif event.key == pygame.K_e:
                      flag_show_exif = not flag_show_exif
                      LightsFlash(3)

            if 'click' in montage_button.handleEvent(event):
                print("[GUI] User clicked Montage button!")
                CaptureMontage()
                
            if 'click' in gif_button.handleEvent(event):
                print("[GUI] User clicked GIF button!")
                CaptureGif()

            if 'click' in quit_button.handleEvent(event):
                print("[GUI] User clicked Quit button!")
                continue_loop = False

        #GPIO button raw reads
        if BTN_A_ACTIVE == False and GPIO.input(BTN_A) == 0:
            BTN_A_ACTIVE = True
            print("Button A raw press detected!")
            APressed(None)

        if BTN_B_ACTIVE == False and GPIO.input(BTN_B) == 0:
            BTN_B_ACTIVE = True
            print("Button B raw press detected!")
            BPressed(None)

        if change_ticks < pygame.time.get_ticks():
            #print "[TICK]"
            ChangeTicks(homescreen_cycle_speed)
            RenderHomeScreen()

        time.sleep(delay_time)

except Exception as exception:
    GPIO.cleanup()
    print ("[EXCEPTION]" + exception.__class__.__name__ + ": " + exception.message)
    traceback.print_exc(file=sys.stdout)

print("Process complete")
#pygame.mixer.quit()
pygame.quit()
GPIO.cleanup()
#Reset the PWM values to low (so LEDs aren't super bright)
print("Resetting GPIO PWM values...")
cmd = 'echo "17=0.05; 18=0.05; 22=0.05; 23=0.05" > /dev/pi-blaster'
os.system(cmd)
exit()
