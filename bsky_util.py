import os
import re
import requests
from atproto import Client, models, exceptions, client_utils
from atproto_client.namespaces.sync_ns import ChatBskyConvoNamespace

# セッション保持ファイル
BSKY_SESSION_FILE = "bsky_session.json"


def message_to_textbuilder(message: str) -> client_utils.TextBuilder:
    """テキストに含まれるタグ情報を分離、タグとして設定する"""
    hashtags = re.findall(r"#\w+", message)
    clean_message = re.sub(r"#\w+", "", message).strip()

    text_builder = client_utils.TextBuilder().text(clean_message)
    for hashtag in hashtags:
        text_builder.text(" ").tag(hashtag, hashtag.lstrip("#"))
    return text_builder


def get_image_bytes(img_url: str) -> bytes:
    """画像URLから画像データを取得"""
    resp = requests.get(img_url)
    resp.raise_for_status()
    return resp.content


class BlueskyUtil:

    def __init__(self) -> None:
        self.client = Client()
        self.chat = ChatBskyConvoNamespace(client=self.client)

    def save_session(self):
        """セッション情報の保存"""
        with open(BSKY_SESSION_FILE, "w") as file:
            file.write(self.client.export_session_string())

    def load_session(self):
        """セッション情報のロード"""
        try:
            print("try relogin.")
            with open(BSKY_SESSION_FILE, "r") as file:
                session_str = file.read()
            return self.client.login(session_string=session_str)
        except (FileNotFoundError, ValueError, exceptions.BadRequestError):
            # ファイルが存在しなかったりトークンが取得できない場合はセッション作成
            print("failed. create session...")
            return self.create_session()

    def create_session(self):
        """セッションの作成"""
        self.client = Client()
        login = self.client.login(
            login=os.getenv("BSKY_USER_NAME"), password=os.getenv("BSKY_APP_PASS")
        )
        self.save_session()
        return login

    def post_external(self, message: str, card: dict, img: bytes):
        """カード付きポスト"""
        message = message_to_textbuilder(message)
        if img:
            upload = self.client.upload_blob(img)
            external = models.AppBskyEmbedExternal.External(
                uri=card.link, title=card.title, thumb=upload.blob, description=""
            )
        else:
            external = models.AppBskyEmbedExternal.External(
                uri=card.link, title=card.title, description=""
            )
        embed = models.AppBskyEmbedExternal.Main(external=external)

        return self.client.send_post(message, embed=embed)

    def post_text(self, message: str):
        """テキストのみのポスト"""
        message = message_to_textbuilder(message)
        self.client.post(message)

    def post_images(self, message: str, image_urls: list):
        """画像付きポスト"""
        message = message_to_textbuilder(message)
        images = []
        for image_url in image_urls:
            images.append(get_image_bytes(image_url))
        self.client.send_images(text=message, images=images)
