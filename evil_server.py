#!/usr/bin/python
# coding: UTF-8

from serial import *
from sys import stdout, stdin, stderr, exit
from flask import Flask, render_template, request, redirect, url_for, jsonify

# シリアルポートはls -l /dev/tty.*
# 自身の名称を app という名前でインスタンス化する
app = Flask(__name__)
ser = None
tocostick = '/dev/tty.usbserial-AHXMLYXU'
# 前進時の推力一覧
# powerDict[推力レベル(1~4)][旋回レベル(0~2)]で推力が入ったタプルが取れる
# タプルは前のほうが常に小さい
powerDict = {
    # 推力1のとき、旋回レベル0なら両舷25%ずつ、1なら20%と35%、2なら0%と40%という意味
    1: {0: (25, 25), 1: (20, 35), 2: (0, 40)},
    2: {0: (50, 50), 1: (25, 60), 2: (0, 70)},
    3: {0: (75, 75), 1: (28, 80), 2: (0, 80)},
    4: {0: (100, 100), 1: (25, 100), 2: (0, 100)},
}


# 終了処理
def DoTerminate():
    print ("... quitting")
    exit(0)


def executeCommand(cmd, msg=''):
    cmd = cmd + "\r\n"
    print ("--> " + cmd)
    writtenBytes = ser.write(cmd)
    return createResponseJson(writtenBytes, cmd, msg)


@app.route('/set.engine')
def getWebCommand():
    # set.engine?power=1&rudder=left&rudder_power=1のように指定
    power = request.args.get('power', type=int)
    rudder = request.args.get('rudder', default='left')
    rudder_power = request.args.get('rudder_power', type=int)
    print(power, rudder, rudder_power)

    # 受け付けるGETパラメータ
    # power: -1, 0, 1, 2, 3, 4
    # -1は逆転。0は停止。1 ~ 4は前進。4は負荷がかかるので長時間使わないこと。
    # 逆転時は舵による制御を無視する。
    # rudder: left, right
    # 舵の左右を決定。
    # rudder_power: 0, 1
    # どれくらい急に舵を切るかを決める。0は切らない、1はゆるやかに、2は全力で。

    if 0 == power:
        return stopEngine()

    if -1 == power:
        return reverseEngine()

    powers = powerDict[power][rudder_power]
    print(powers)
    # 左方向に旋回したいときは、右側の出力を大きくする
    if 'left' == rudder:
        leftPowerPercent, rightPowerPercent = powers
    # 右方向に旋回したいときは、左側の出力を大きくする
    if 'right' == rudder:
        rightPowerPercent, leftPowerPercent = powers

    command = generateForwardCommand(leftPowerPercent, rightPowerPercent)
    msg = 'left: {0}, right: {1}'.format(leftPowerPercent, rightPowerPercent)
    return executeCommand(command, msg)


def generateForwardCommand(leftPowerPercent=0, rightPowerPercent=0):
    # 左右のモータのDuty比を指定して、前進用のコマンドを生成
    baseCommand = ':7880010303{leftPower:0>4X}{rightPower:0>4X}FFFFFFFFX'
    maxPowerInDec = 1024
    leftPowerInDec = int(maxPowerInDec * leftPowerPercent / 100)
    rightPowerInDec = int(maxPowerInDec * rightPowerPercent / 100)
    return baseCommand.format(
        leftPower=leftPowerInDec,
        rightPower=rightPowerInDec
    )


@app.route('/forward')
def forward3():
    cmd = ':788001030303000300FFFFFFFFFF'
    msg = 'forward3 75%'
    return executeCommand(cmd, msg)


@app.route('/stop')
def stopEngine():
    # 停船
    # モータの出力を0%に
    cmd = ':788001030300000000FFFFFFFF05'
    msg = 'stop'
    return executeCommand(cmd, msg)


@app.route('/reverse')
def reverseEngine():
    # 逆進
    cmd = ':788001000302CD02CDFFFFFFFF6A'
    msg = 'reverse'
    return executeCommand(cmd, msg)


def createResponseJson(writtenBytes, sendCommand, Message=''):
    response_dict = {
        "writtenBytes": writtenBytes,
        "sendCommand": sendCommand,
        "Message": Message
    }
    return jsonify(Result=response_dict)


if __name__ == '__main__':
    # パラメータの確認
    # 第一引数: シリアルポート名を指定可能。なければデフォルトを使用
    if len(sys.argv) == 2:
        tocostick = sys.argv[1]

    # シリアルポートを開く
    try:
        ser = Serial(tocostick, 115200, timeout=0.1)
        print ("open serial port: %s" % tocostick)
    except:
        print ("cannot open serial port: %s" % tocostick)
        exit(1)

    # サーバを起動。どこからでもアクセスできるように
    app.config["CACHE_TYPE"] = "null"
    app.debug = True
    app.run(host='0.0.0.0')
